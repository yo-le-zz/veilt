"""
veilt.integrity
================
Defense-in-depth tamper detection.

Primary integrity is already guaranteed by AES-256-GCM's built-in
authentication tag (any single-bit change anywhere in the ciphertext
makes decryption fail). This module adds an OPTIONAL, independent
second layer: a keyed HMAC-SHA256 over `entry_id || ciphertext`, using
a key derived separately from the encryption key (see
`crypto.derive_subkey`). It gives:

  - An explicit, fast PASS/FAIL check (`veilt integrity`) that doesn't
    require attempting a full decryption.
  - Protection against storage-layer corruption scenarios that could
    otherwise look like "just an empty/missing file" rather than a
    clear integrity failure.
"""
from __future__ import annotations

import hashlib
import hmac

from . import crypto


def compute_entry_hash(entry_id: str, ciphertext: bytes, hmac_key: bytes) -> str:
    message = entry_id.encode("utf-8") + b":" + ciphertext
    return crypto.hmac_sha256(hmac_key, message)


def verify_entry_hash(entry_id: str, ciphertext: bytes, hmac_key: bytes, expected_hash: str) -> bool:
    actual = compute_entry_hash(entry_id, ciphertext, hmac_key)
    return hmac.compare_digest(actual, expected_hash)


def hash_raw(data: bytes) -> str:
    """Plain SHA-256 hash, used only for non-secret diagnostic fingerprints
    (e.g. displaying a short hash in `veilt see`) - never for anything
    security-relevant."""
    return hashlib.sha256(data).hexdigest()
