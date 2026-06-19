"""
veil.exceptions
================
Exception hierarchy for VEIL. Catching `veil.VeilError` catches everything
VEIL can raise.
"""


class VeilError(Exception):
    """Base exception for every error raised by VEIL."""


class ConfigError(VeilError):
    """The vault configuration is missing, unreadable, or corrupted."""


class AuthenticationError(VeilError):
    """The supplied master password is incorrect."""


class DecryptionError(VeilError):
    """AES-256-GCM authentication failed: wrong key or tampered ciphertext."""


class IntegrityError(VeilError):
    """The optional HMAC integrity layer detected a mismatch."""


class EntryNotFoundError(VeilError):
    """No entry exists for the requested id."""


class PanicModeError(VeilError):
    """The native engine has detected a suspicious access pattern and is
    rejecting operations / returning decoy data."""


class NativeEngineError(VeilError):
    """The native (C++) engine could not be loaded or raised an error."""


class ElevationError(VeilError):
    """Requesting administrator/root privileges failed."""
