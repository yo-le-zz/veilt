# =========================================================
# VAULT PACKAGE EXPORTS
#
# This subpackage is the encryption/storage engine internals
# (crypto, integrity, daemon, anti-memory-dump, audit log).
# Only `Vault` and `validate_password_strength` are public API -
# everything else here is an implementation detail of `core.py`
# and is intentionally NOT re-exported with `import *`.
# =========================================================

from .core import Vault, validate_password_strength

__all__ = ["Vault", "validate_password_strength"]
