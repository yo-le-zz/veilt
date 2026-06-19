"""
veil.vault
===========
High-level public API.

    import veil

    with veil.Vault(password="My-Strong-P@ssw0rd!") as vault:
        vault.set("api_key", "sk-...")
        secret = vault.get("api_key")

That's the whole interface most projects need: give it a password, get
an encrypted, memory-locked, tamper-evident secret store. Everything
else (TTL leases, --admin hardening, OS keyring quick-unlock, audit
log) is opt-in on top of that.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from . import config as cfgmod
from . import crypto
from . import integrity
from ._version import VERSION
from .antimem import ThreatScanner
from .daemon import Daemon, EntryStatus
from .exceptions import (
    AuthenticationError,
    DecryptionError,
    EntryNotFoundError,
    IntegrityError,
    PanicModeError,
    VeilError,
)
from .logs import AuditLog, DeleteReason, EventType
from .memory import create_engine, is_native_available

_SENTINEL = object()

_WEAK_PASSWORDS = {
    "password", "12345678", "qwerty", "abc12345", "password123",
    "admin", "letmein", "welcome", "monkey", "dragon",
    "master", "sunshine", "iloveyou", "football",
}


def validate_password_strength(password: str) -> None:
    """Raises ValueError with a clear reason if the password is too weak.
    Used for the master password of a brand-new vault only - existing
    vaults are never re-validated just to unlock them."""
    if not password or not password.strip():
        raise ValueError("password cannot be empty")
    if len(password) < 8:
        raise ValueError("password too short (minimum 8 characters)")
    if password.lower() in _WEAK_PASSWORDS:
        raise ValueError("this password is too common/weak")
    classes = sum([
        any(c.isupper() for c in password),
        any(c.islower() for c in password),
        any(c.isdigit() for c in password),
        any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?/~`" for c in password),
    ])
    if classes < 3:
        raise ValueError(
            "password must contain at least 3 of: uppercase, lowercase, digits, special characters"
        )


class Vault:
    """
    A self-contained, encrypted secret vault.

    Parameters
    ----------
    password : str
        Master password. Creates a brand-new vault on first use, or
        unlocks ("unseals") an existing one.
    name : str
        Logical vault name - run several independent vaults on the same
        machine by giving them different names. Default: "default".
    storage : "ram" | "disk"
        "ram"  - secrets exist only in locked process memory; wiped the
                 moment close()/seal() is called or the process exits.
        "disk" - secrets are additionally persisted, encrypted-at-rest,
                 under the vault's data directory, surviving restarts.
    admin : bool
        Request the extra hardening unlocked by elevated privileges
        (unrestricted memory locking, system-wide storage location).
        VEIL never elevates the process for you - call
        `veil.elevate.request_admin()` yourself first if you need to
        re-launch with privileges, then pass admin=True.
    hmac_enabled : bool
        Extra, independent HMAC-SHA256 integrity layer on top of AES-GCM's
        own authentication. Default True.
    max_access_per_window / min_access_interval_ms :
        Anti-dump heuristics: an entry read more than `max_access_per_window`
        times, or read again within `min_access_interval_ms` of the
        previous read, trips panic mode for this vault instance.
    """

    def __init__(
        self,
        password: str,
        name: str = "default",
        storage: str = "ram",
        admin: bool = False,
        hmac_enabled: Optional[bool] = None,
        language: Optional[str] = None,
        ram_limit: Optional[int] = None,
        disk_limit: Optional[int] = None,
        max_access_per_window: int = 30,
        min_access_interval_ms: int = 5,
    ) -> None:
        if storage not in ("ram", "disk"):
            raise ValueError("storage must be 'ram' or 'disk'")

        self.name = name
        self.storage = storage
        self.admin = admin
        self._data_dir = cfgmod.get_data_dir(use_system=admin) / name
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._engine = create_engine(max_access_per_window, min_access_interval_ms)
        if admin:
            try:
                self._engine.raise_memory_lock_limit()
            except Exception:
                pass

        config_path = self._data_dir / cfgmod.CONFIG_FILENAME
        self._config = cfgmod.load_config_at(config_path)
        is_new = self._config is None

        if is_new:
            validate_password_strength(password)
            self._config = dict(cfgmod.CONFIG_TEMPLATE)
            self._config.update({
                "version": VERSION,
                "storage": storage,
                "ram_limit": ram_limit,
                "disk_limit": disk_limit,
                "password_hash": crypto.hash_password(password),
                "salt": crypto.generate_salt(),
                "hmac_enabled": hmac_enabled if hmac_enabled is not None else True,
                "language": language or "fr",
                "initialized": True,
            })
            cfgmod.save_config_at(self._config, config_path)
        else:
            if not crypto.verify_password(password, self._config["password_hash"]):
                raise AuthenticationError("Invalid master password")
            if crypto.needs_rehash(self._config["password_hash"]):
                self._config["password_hash"] = crypto.hash_password(password)
                cfgmod.save_config_at(self._config, config_path)
            # Storage mode is fixed at vault creation time, not re-selectable
            # per session - silently honoring a different `storage=` value
            # passed in here would mean the exact same vault behaves as
            # RAM-only in one process and disk-persisted in another.
            self.storage = self._config.get("storage", storage)

        self._config_path = config_path

        # The master key only ever lives here, in locked process memory,
        # for as long as this Vault object stays unsealed.
        self._master_key = crypto.derive_master_key(password, self._config["salt"])
        self._hmac_key = crypto.derive_subkey(self._master_key, "veil-integrity-hmac")
        self._chain_key = crypto.derive_subkey(self._master_key, "veil-audit-chain")
        self._sealed = False

        self._audit = AuditLog(self._data_dir / "audit.log", self._chain_key)
        self._daemon = Daemon(on_expire=self._on_entry_expired)
        self._daemon.start()
        self._scanner = ThreatScanner()

        if self.storage == "disk":
            self._load_index()

        self._audit.log(EventType.VAULT_UNSEALED, details={"storage": storage, "admin": admin})

    # ----------------------------------------------------------------- #
    # Context manager / lifecycle
    # ----------------------------------------------------------------- #
    def __enter__(self) -> "Vault":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __repr__(self) -> str:
        state = "sealed" if self._sealed else "unsealed"
        return f"<veil.Vault name={self.name!r} storage={self.storage!r} {state}>"

    def close(self) -> None:
        """Seal the vault: wipe the master key and every in-memory secret.
        Safe to call multiple times."""
        if self._sealed:
            return
        self._daemon.stop()
        self._engine.clear_all()
        self._master_key = b"\x00" * len(self._master_key)
        self._hmac_key = b"\x00" * len(self._hmac_key)
        self._chain_key = b"\x00" * len(self._chain_key)
        self._sealed = True
        self._audit.log(EventType.VAULT_SEALED)

    seal = close  # HashiCorp-Vault-style alias

    # ----------------------------------------------------------------- #
    # Internal helpers
    # ----------------------------------------------------------------- #
    def _data_file(self, entry_id: str) -> Path:
        return self._data_dir / f"{entry_id}.veil"

    def _index_path(self) -> Path:
        return self._data_dir / "index.json"

    def _load_index(self) -> None:
        """Restore entry metadata (status/ttl/data_hash/access_count) that
        was persisted on a previous process's exit - this is what lets
        `veil see` / `veil integrity` / TTL leases work correctly across
        separate CLI invocations of a disk-backed vault, not just within
        one long-running library process."""
        index = cfgmod.load_config_at(self._index_path())
        if not index:
            return
        for entry_id, meta in index.items():
            self._daemon.restore(entry_id, meta)

    def _save_index(self) -> None:
        if self.storage != "disk":
            return
        try:
            cfgmod.save_config_at(self._daemon.export_index(), self._index_path())
        except Exception:
            pass

    def _ensure_unsealed(self) -> None:
        if self._sealed:
            raise VeilError("This Vault is sealed (closed). Create a new Vault(...) instance to continue.")
        if self._engine.is_panic_mode():
            raise PanicModeError(
                "PANIC MODE is active: a suspicious access pattern was detected. "
                "The operation was rejected. Call reset_panic() only after you have "
                "reviewed the audit log and are confident this was a false positive."
            )

    def _check_threats(self, action: str) -> None:
        report = self._scanner.scan()
        level = report.get("threat_level", "LOW")
        if level in ("HIGH", "CRITICAL"):
            self._audit.log(EventType.ANTI_DUMP_TRIGGERED, details={"action": action, **report})
            if level == "CRITICAL":
                self._engine.force_panic()
                raise PanicModeError("SECURITY ALERT: memory-inspection tooling detected - access denied")

    def _on_entry_expired(self, entry_id: str) -> None:
        try:
            self._engine.erase_entry(entry_id)
            data_file = self._data_file(entry_id)
            if data_file.exists():
                data_file.unlink()
            self._daemon.remove(entry_id)
            self._save_index()
            self._audit.log(EventType.ENTRY_EXPIRED, entry_id=entry_id)
        except Exception:
            pass

    # ----------------------------------------------------------------- #
    # Public CRUD API
    # ----------------------------------------------------------------- #
    def set(self, entry_id: str, value: Union[str, bytes], ttl: Optional[float] = None) -> None:
        """Encrypt and store `value` under `entry_id`.

        `ttl`: optional lease in seconds - the entry is automatically and
        securely wiped after it elapses (inspired by HashiCorp Vault's
        dynamic-secret leases, simplified to a local timer)."""
        self._ensure_unsealed()
        self._check_threats("set")

        if isinstance(value, str):
            value = value.encode("utf-8")

        aad = entry_id.encode("utf-8")
        ciphertext = crypto.encrypt(value, self._master_key, associated_data=aad)
        data_hash = (
            integrity.compute_entry_hash(entry_id, ciphertext, self._hmac_key)
            if self._config.get("hmac_enabled", True)
            else None
        )

        self._engine.store(entry_id, ciphertext)
        if self.storage == "disk":
            self._data_file(entry_id).write_bytes(ciphertext)

        self._daemon.register(entry_id, data_hash=data_hash, ttl=ttl)
        self._save_index()
        self._audit.log(
            EventType.ENTRY_CREATED, entry_id=entry_id,
            details={"ttl": ttl, "storage": self.storage},
        )

    # Alias matching the keyring/Credential-Manager-style vocabulary.
    set_password = set

    def get(self, entry_id: str, default: Any = _SENTINEL) -> str:
        """Retrieve and decrypt the value stored under `entry_id`.

        Raises EntryNotFoundError unless `default` is given, in which
        case it is returned instead."""
        self._ensure_unsealed()
        self._check_threats("get")

        ciphertext = self._engine.get(entry_id)

        # The native/fallback engine may have just tripped panic mode as a
        # *result* of this very call (rapid re-access / over-quota reads).
        # Surface that distinctly from "no such entry" - returning decoy
        # bytes from .get() is an internal anti-forensic signal, not a
        # value callers should ever see compared against real data.
        if self._engine.is_panic_mode():
            raise PanicModeError(
                "PANIC MODE triggered: suspicious access pattern detected for "
                f"'{entry_id}'. The operation was rejected."
            )

        if ciphertext is None and self.storage == "disk":
            data_file = self._data_file(entry_id)
            if data_file.exists():
                ciphertext = data_file.read_bytes()
                self._engine.store(entry_id, ciphertext)
                ciphertext = self._engine.get(entry_id)
                if self._engine.is_panic_mode():
                    raise PanicModeError(
                        f"PANIC MODE triggered while reloading '{entry_id}' from disk."
                    )

        if ciphertext is None:
            if default is not _SENTINEL:
                return default
            raise EntryNotFoundError(f"No entry found for id '{entry_id}'")

        meta = self._daemon.get_status(entry_id)
        if self._config.get("hmac_enabled", True) and meta.get("data_hash"):
            if not integrity.verify_entry_hash(entry_id, ciphertext, self._hmac_key, meta["data_hash"]):
                self._daemon.update_status(entry_id, EntryStatus.CORRUPTED)
                self._audit.log(EventType.INTEGRITY_MISMATCH, entry_id=entry_id)
                raise IntegrityError(f"Integrity check failed for '{entry_id}': data may be corrupted or tampered with")

        aad = entry_id.encode("utf-8")
        try:
            plaintext = crypto.decrypt(ciphertext, self._master_key, associated_data=aad)
        except DecryptionError:
            self._audit.log(EventType.AUTH_FAILED, entry_id=entry_id)
            raise

        self._daemon.increment_access(entry_id)
        self._audit.log(EventType.ENTRY_ACCESSED, entry_id=entry_id)
        return plaintext.decode("utf-8")

    get_password = get

    def delete(self, entry_id: str) -> bool:
        """Securely wipe an entry (overwrite, then erase). Returns True
        if the entry existed."""
        self._ensure_unsealed()
        existed = self._engine.erase_entry(entry_id)
        data_file = self._data_file(entry_id)
        if data_file.exists():
            data_file.unlink()
            existed = True
        self._daemon.remove(entry_id)
        self._save_index()
        if existed:
            self._audit.log(EventType.ENTRY_DELETED, entry_id=entry_id, reason=DeleteReason.USER_REQUEST.value)
        return existed

    delete_password = delete

    def exists(self, entry_id: str) -> bool:
        return self._engine.get(entry_id) is not None or self._data_file(entry_id).exists()

    def list_entries(self) -> List[Dict[str, Any]]:
        self._ensure_unsealed()
        return [{"id": entry_id, **meta} for entry_id, meta in self._daemon.get_all().items()]

    # ----------------------------------------------------------------- #
    # Security / status
    # ----------------------------------------------------------------- #
    @property
    def is_panic(self) -> bool:
        return self._engine.is_panic_mode()

    def reset_panic(self) -> None:
        """Explicitly re-arm the vault after reviewing the audit log and
        confirming a panic-mode trigger was a false positive. Never
        automatic."""
        self._engine.reset_panic()

    def verify_audit_log(self) -> bool:
        return self._audit.verify_chain()

    def audit_events(self, limit: int = 50) -> List[Dict]:
        return self._audit.read_all(limit)

    def status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "storage": self.storage,
            "sealed": self._sealed,
            "panic_mode": self.is_panic,
            "entries_in_memory": self._engine.size(),
            "native_engine": is_native_available(),
            "admin": self.admin,
            "hmac_enabled": self._config.get("hmac_enabled", True),
            "audit_chain_valid": self.verify_audit_log(),
            "data_dir": str(self._data_dir),
        }

    def purge(self) -> None:
        """Irreversibly wipe this vault: every entry, the config, and the
        audit log. There is no undo."""
        self._audit.log(EventType.VAULT_PURGED)
        self._engine.clear_all()
        self._daemon.stop()
        if self._data_dir.exists():
            shutil.rmtree(self._data_dir, ignore_errors=True)
        self._sealed = True
