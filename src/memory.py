"""
veil.memory
============
Thin wrapper that picks the compiled native engine (`veil._veil_native`,
written in C++) when available, and transparently falls back to a pure
-Python engine with the exact same semantics otherwise - so `import veil`
never hard-fails just because a C++ compiler wasn't available when the
package was installed (e.g. an unusual platform not covered by the
prebuilt wheels). The fallback has the same store/get/erase/clear_all
API and the same fixed panic-mode logic, but cannot pin memory with
mlock/VirtualLock.
"""
from __future__ import annotations

import threading
import time
import warnings
from typing import Optional

try:
    from . import _veil_native as _native  # type: ignore
    _NATIVE_AVAILABLE = True
except ImportError:
    _native = None  # type: ignore
    _NATIVE_AVAILABLE = False


def is_native_available() -> bool:
    return _NATIVE_AVAILABLE


class _PurePythonStore:
    """Fallback engine, same semantics as the C++ SecureStore."""

    FAKE_BLOCK = b"VEIL::FAKE_DATA_BLOCK"

    def __init__(self, max_access_per_window: int = 30, min_interval_ms: int = 5):
        self._store: dict = {}
        self._lock = threading.Lock()
        self._panic = False
        self._max_access = max_access_per_window
        self._min_interval = min_interval_ms / 1000.0

    def store(self, id: str, data: bytes) -> None:
        with self._lock:
            if self._panic:
                return
            self._store[id] = {"data": bytearray(data), "count": 0, "last": time.monotonic()}

    def get(self, id: str) -> Optional[bytes]:
        with self._lock:
            if self._panic:
                return self.FAKE_BLOCK
            entry = self._store.get(id)
            if entry is None:
                return None

            prev = entry["last"]
            now = time.monotonic()
            entry["count"] += 1
            entry["last"] = now

            too_fast = entry["count"] > 1 and (now - prev) < self._min_interval
            too_many = entry["count"] > self._max_access
            if too_fast or too_many:
                self._panic = True
                return self.FAKE_BLOCK

            return bytes(entry["data"])

    def erase_entry(self, id: str) -> bool:
        with self._lock:
            entry = self._store.pop(id, None)
            if entry is None:
                return False
            buf = entry["data"]
            for i in range(len(buf)):
                buf[i] = 0
            return True

    def clear_all(self) -> None:
        with self._lock:
            for entry in self._store.values():
                buf = entry["data"]
                for i in range(len(buf)):
                    buf[i] = 0
            self._store.clear()
            self._panic = False

    def fake_dump(self) -> bytes:
        return self.FAKE_BLOCK

    def size(self) -> int:
        with self._lock:
            return len(self._store)

    def is_panic_mode(self) -> bool:
        with self._lock:
            return self._panic

    def reset_panic(self) -> None:
        with self._lock:
            self._panic = False

    def force_panic(self) -> None:
        with self._lock:
            self._panic = True

    def raise_memory_lock_limit(self) -> bool:
        return False  # not supported without the native engine


def create_engine(max_access_per_window: int = 30, min_interval_ms: int = 5):
    if _NATIVE_AVAILABLE:
        return _native.SecureStore(max_access_per_window, min_interval_ms)
    warnings.warn(
        "VEIL native engine is not available on this platform - falling back "
        "to the pure-Python engine. Memory locking (mlock/VirtualLock) and "
        "process anti-dump hardening are disabled in this mode. Install a "
        "C++ compiler and reinstall (`pip install --force-reinstall veil-vault`) "
        "to enable full protection.",
        RuntimeWarning,
        stacklevel=2,
    )
    return _PurePythonStore(max_access_per_window, min_interval_ms)
