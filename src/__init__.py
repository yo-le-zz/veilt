"""
VEIL - Secure, encrypted, in-memory/on-disk secret vault for Python.

    import veilt

    with veilt.Vault(password="My-Strong-P@ssw0rd!") as vault:
        vault.set("api_key", "sk-...")
        print(vault.get("api_key"))

Author : yolezz
License: MIT
"""
from ._version import VERSION
from .vault import Vault, validate_password_strength
from .exceptions import (
    AuthenticationError,
    ConfigError,
    DecryptionError,
    ElevationError,
    EntryNotFoundError,
    IntegrityError,
    NativeEngineError,
    PanicModeError,
    VeilError,
)
from .elevate import is_admin, request_admin
from .memory import is_native_available
from . import i18n
from . import osvault

__version__ = VERSION

__all__ = [
    "Vault",
    "validate_password_strength",
    "VeilError",
    "AuthenticationError",
    "ConfigError",
    "DecryptionError",
    "ElevationError",
    "EntryNotFoundError",
    "IntegrityError",
    "NativeEngineError",
    "PanicModeError",
    "is_admin",
    "request_admin",
    "is_native_available",
    "i18n",
    "osvault",
    "__version__",
]


def quick_set(entry_id: str, value: str, password: str, vault_name: str = "default", **kwargs) -> None:
    """One-liner, keyring-style convenience function:
    `veilt.quick_set("github_token", "ghp_xxx", password="...")`

    Defaults to `storage="disk"` (encrypted-at-rest) since, unlike a
    long-running `Vault()` instance, two separate quick_set()/quick_get()
    calls have no shared memory to persist a `storage="ram"` value in -
    pass storage="ram" explicitly only if you really want write-only,
    self-destructing-on-return semantics."""
    kwargs.setdefault("storage", "disk")
    with Vault(password=password, name=vault_name, **kwargs) as vault:
        vault.set(entry_id, value)


def quick_get(entry_id: str, password: str, vault_name: str = "default", **kwargs) -> str:
    """One-liner, keyring-style convenience function:
    `veilt.quick_get("github_token", password="...")`"""
    kwargs.setdefault("storage", "disk")
    with Vault(password=password, name=vault_name, **kwargs) as vault:
        return vault.get(entry_id)
