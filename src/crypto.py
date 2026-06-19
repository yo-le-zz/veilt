"""
veilt.crypto
============
Modern cryptographic primitives for VEIL.

Replaces the original SHA-256 password hashing / PBKDF2-150k / Fernet
(AES-128-CBC+HMAC) stack with:

  - Argon2id for BOTH password verification and master-key derivation
    (memory-hard: far more resistant to GPU/ASIC brute-forcing than
    PBKDF2 or a raw SHA-256 hash).
  - AES-256-GCM (AEAD) for data encryption - authenticated, so any
    tampering with the ciphertext is detected at decryption time,
    instead of needing a bolted-on separate hash check.
  - HKDF-SHA256 to derive independent sub-keys (per-purpose: entry
    encryption is bound to the master key directly via AEAD associated
    data; the HMAC integrity layer and the audit-log hash-chain each
    get their OWN key, derived from - but not equal to - the master
    key, so compromising one use can never be replayed against another).
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Optional

from argon2 import PasswordHasher
from argon2 import exceptions as argon2_exceptions
from argon2.low_level import Type as Argon2Type
from argon2.low_level import hash_secret_raw
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .exceptions import DecryptionError

# =========================================================
# CONSTANTS
# =========================================================
AES_KEY_LEN = 32          # AES-256
GCM_NONCE_LEN = 12        # 96-bit nonce, the size recommended for GCM
GCM_TAG_LEN = 16
SALT_LEN_BYTES = 16

ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST_KIB = 65536   # 64 MiB
ARGON2_PARALLELISM = 4
ARGON2_HASH_LEN = 32

_password_hasher = PasswordHasher(
    time_cost=ARGON2_TIME_COST,
    memory_cost=ARGON2_MEMORY_COST_KIB,
    parallelism=ARGON2_PARALLELISM,
    hash_len=ARGON2_HASH_LEN,
)


# =========================================================
# SALT
# =========================================================
def generate_salt(length: int = SALT_LEN_BYTES) -> str:
    """Cryptographically random hex-encoded salt, unique per vault."""
    return secrets.token_hex(length)


# =========================================================
# PASSWORD HASHING (storage / verification of the master password)
# =========================================================
def hash_password(password: str) -> str:
    """Argon2id hash of the master password. The returned string already
    encodes its own salt and parameters - safe to store as-is in config."""
    return _password_hasher.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    """Constant-time verification. Never raises on a wrong password -
    returns False instead, so callers can't accidentally branch on
    exception type and leak timing/behavioural information."""
    try:
        return _password_hasher.verify(stored_hash, password)
    except (argon2_exceptions.VerifyMismatchError, argon2_exceptions.InvalidHash):
        return False


def needs_rehash(stored_hash: str) -> bool:
    """True if the stored hash used weaker parameters than the current
    defaults (lets VEIL transparently upgrade old vaults on next unlock)."""
    try:
        return _password_hasher.check_needs_rehash(stored_hash)
    except argon2_exceptions.InvalidHash:
        return True


# =========================================================
# KEY DERIVATION
# =========================================================
def derive_master_key(password: str, salt_hex: str) -> bytes:
    """
    Derive a 32-byte master key from password + salt using Argon2id in
    raw KDF mode (memory-hard - this is what actually protects you if
    your encrypted vault file is ever stolen and brute-forced offline).
    """
    salt_bytes = bytes.fromhex(salt_hex)
    return hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt_bytes,
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST_KIB,
        parallelism=ARGON2_PARALLELISM,
        hash_len=AES_KEY_LEN,
        type=Argon2Type.ID,
    )


def derive_subkey(master_key: bytes, purpose: str, length: int = 32) -> bytes:
    """
    HKDF-SHA256 derivation of an independent sub-key from the master key,
    bound to `purpose` so different uses (HMAC integrity, audit-log
    chaining, ...) can never be confused with one another or with the
    master key itself.
    """
    hkdf = HKDF(algorithm=hashes.SHA256(), length=length, salt=None, info=purpose.encode("utf-8"))
    return hkdf.derive(master_key)


# =========================================================
# AEAD ENCRYPTION (AES-256-GCM)
# =========================================================
def encrypt(data: bytes, key: bytes, associated_data: Optional[bytes] = None) -> bytes:
    """
    AES-256-GCM authenticated encryption.
    Output layout: nonce (12 bytes) || ciphertext || authentication tag (16 bytes)
    `associated_data` (e.g. the entry id) is authenticated but not encrypted,
    binding the ciphertext to its identity (prevents swapping entries).
    """
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(GCM_NONCE_LEN)
    ciphertext = aesgcm.encrypt(nonce, data, associated_data)
    return nonce + ciphertext


def decrypt(blob: bytes, key: bytes, associated_data: Optional[bytes] = None) -> bytes:
    if len(blob) < GCM_NONCE_LEN + GCM_TAG_LEN:
        raise DecryptionError("Ciphertext is too short to be valid - it is corrupted or truncated")
    nonce, ciphertext = blob[:GCM_NONCE_LEN], blob[GCM_NONCE_LEN:]
    aesgcm = AESGCM(key)
    try:
        return aesgcm.decrypt(nonce, ciphertext, associated_data)
    except Exception as exc:
        raise DecryptionError("Authentication failed: wrong password, or the data was tampered with") from exc


# =========================================================
# HMAC (defense-in-depth integrity layer, see veilt.integrity)
# =========================================================
def hmac_sha256(key: bytes, data: bytes) -> str:
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def verify_hmac(key: bytes, data: bytes, expected_hex: str) -> bool:
    return hmac.compare_digest(hmac_sha256(key, data), expected_hex)
