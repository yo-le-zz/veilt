"""
veil.logs
==========
Structured, tamper-evident audit log.

Every entry is cryptographically chained to the previous one:

    chain_hash[n] = HMAC(chain_key, prev_hash[n] || entry[n])

This mirrors the integrity guarantee of HashiCorp Vault's audit device
(you can prove the log wasn't edited after the fact) without needing a
server: it's just an HMAC chain over a local append-only file. Run
`veil audit verify` (or `AuditLog.verify_chain()`) at any time to detect
whether any past line was edited, reordered, or deleted.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from . import crypto


class EventType(str, Enum):
    ENTRY_CREATED = "ENTRY_CREATED"
    ENTRY_ACCESSED = "ENTRY_ACCESSED"
    ENTRY_DELETED = "ENTRY_DELETED"
    ENTRY_EXPIRED = "ENTRY_EXPIRED"
    ENTRY_CRASHED = "ENTRY_CRASHED"
    AUTH_FAILED = "AUTH_FAILED"
    INTEGRITY_MISMATCH = "INTEGRITY_MISMATCH"
    PANIC_TRIGGERED = "PANIC_TRIGGERED"
    ANTI_DUMP_TRIGGERED = "ANTI_DUMP_TRIGGERED"
    VAULT_UNSEALED = "VAULT_UNSEALED"
    VAULT_SEALED = "VAULT_SEALED"
    VAULT_PURGED = "VAULT_PURGED"


class DeleteReason(str, Enum):
    USER_REQUEST = "USER_REQUEST"
    AUTH_FAILURE = "AUTH_FAILURE"
    INTEGRITY_MISMATCH = "INTEGRITY_MISMATCH"
    PANIC_WIPE = "PANIC_WIPE"
    ANTI_DUMP = "ANTI_DUMP"
    EXPIRED = "EXPIRED"


class AuditLog:
    GENESIS_HASH = "0" * 64

    def __init__(self, log_path: Path, chain_key: bytes):
        self._path = log_path
        self._key = chain_key
        self._lock = threading.Lock()
        self._last_hash = self._read_last_hash()

    def _read_last_hash(self) -> str:
        if not self._path.exists():
            return self.GENESIS_HASH
        last = self.GENESIS_HASH
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        last = entry.get("chain_hash", last)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass
        return last

    def log(self, event_type, entry_id: Optional[str] = None,
            reason: Optional[str] = None, details: Optional[Dict] = None) -> None:
        with self._lock:
            event_value = event_type.value if isinstance(event_type, EventType) else str(event_type)
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": event_value,
                "entry_id": entry_id,
                "reason": reason,
                "details": details or {},
                "prev_hash": self._last_hash,
            }
            serialized = json.dumps(payload, sort_keys=True)
            chain_hash = crypto.hmac_sha256(self._key, (self._last_hash + serialized).encode("utf-8"))
            payload["chain_hash"] = chain_hash

            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
            self._last_hash = chain_hash

    def verify_chain(self) -> bool:
        """Replays the whole chain and verifies every HMAC link.
        Returns True if the log is intact (untampered, unedited)."""
        if not self._path.exists():
            return True
        prev = self.GENESIS_HASH
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        return False
                    claimed = entry.pop("chain_hash", None)
                    if claimed is None or entry.get("prev_hash") != prev:
                        return False
                    serialized = json.dumps(entry, sort_keys=True)
                    if not crypto.verify_hmac(self._key, (prev + serialized).encode("utf-8"), claimed):
                        return False
                    prev = claimed
        except OSError:
            return False
        return True

    def read_all(self, limit: int = 100) -> List[Dict]:
        if not self._path.exists():
            return []
        with open(self._path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        out: List[Dict] = []
        for line in reversed(lines[-limit:]):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def clear(self) -> None:
        with self._lock:
            if self._path.exists():
                os.remove(self._path)
            self._last_hash = self.GENESIS_HASH
