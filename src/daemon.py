"""
veil.daemon
============
Background thread tracking entry status (ACTIVE / EXPIRED / DELETED /
CORRUPTED) and enforcing optional TTL leases on secrets - a simplified,
fully-local take on HashiCorp Vault's lease/revocation model (no server,
no network: just a timer inside your own process).

Unlike the original implementation, this is a plain class instantiated
once per Vault - not module-level global state. That fixes a real bug
class: the old globals (`INDEX`, `RUNNING`, ...) meant two Vault-like
objects in the same process silently shared and corrupted each other's
data, and made the test suite flaky.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Dict, Optional


class EntryStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DELETED = "DELETED"
    EXPIRED = "EXPIRED"
    CRASHED = "CRASHED"
    CORRUPTED = "CORRUPTED"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Daemon:
    def __init__(self, on_expire: Optional[Callable[[str], None]] = None, interval: float = 1.0):
        self._index: Dict[str, dict] = {}
        self._lock = threading.RLock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._on_expire = on_expire
        self._interval = interval

    # ----------------------------------------------------------------- #
    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="veil-daemon")
        self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self._running = False
            self._index.clear()

    def _loop(self) -> None:
        while True:
            with self._lock:
                if not self._running:
                    return
            self._check_expirations()
            time.sleep(self._interval)

    def _check_expirations(self) -> None:
        now = time.time()
        expired = []
        with self._lock:
            for entry_id, meta in self._index.items():
                expires_at = meta.get("expires_at")
                if expires_at is not None and now >= expires_at and meta["status"] == EntryStatus.ACTIVE.value:
                    meta["status"] = EntryStatus.EXPIRED.value
                    expired.append(entry_id)
        for entry_id in expired:
            if self._on_expire:
                try:
                    self._on_expire(entry_id)
                except Exception:
                    pass

    # ----------------------------------------------------------------- #
    def register(self, entry_id: str, data_hash: Optional[str] = None, ttl: Optional[float] = None) -> None:
        with self._lock:
            self._index[entry_id] = {
                "status": EntryStatus.ACTIVE.value,
                "created_at": _now_iso(),
                "last_seen": _now_iso(),
                "data_hash": data_hash,
                "access_count": 0,
                "ttl": ttl,
                "expires_at": (time.time() + ttl) if ttl else None,
            }

    def update_status(self, entry_id: str, status: EntryStatus, reason: Optional[str] = None) -> None:
        with self._lock:
            if entry_id in self._index:
                self._index[entry_id]["status"] = status.value if isinstance(status, EntryStatus) else status
                self._index[entry_id]["last_seen"] = _now_iso()
                if reason:
                    self._index[entry_id]["reason"] = reason

    def increment_access(self, entry_id: str) -> None:
        with self._lock:
            if entry_id in self._index:
                self._index[entry_id]["access_count"] += 1
                self._index[entry_id]["last_seen"] = _now_iso()

    def get_status(self, entry_id: str) -> dict:
        with self._lock:
            return dict(self._index.get(entry_id, {}))

    def get_all(self) -> Dict[str, dict]:
        with self._lock:
            return {k: dict(v) for k, v in self._index.items()}

    def remove(self, entry_id: str) -> None:
        with self._lock:
            self._index.pop(entry_id, None)

    def restore(self, entry_id: str, meta: dict) -> None:
        """Re-insert metadata loaded from a persisted index, as-is (does
        NOT reset created_at/access_count/expires_at - those are wall-clock
        values, valid across a process restart)."""
        with self._lock:
            self._index[entry_id] = dict(meta)

    def export_index(self) -> Dict[str, dict]:
        with self._lock:
            return {k: dict(v) for k, v in self._index.items()}
