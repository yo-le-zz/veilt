import pytest

from veil import crypto
from veil.exceptions import DecryptionError


def test_password_hash_and_verify_roundtrip():
    h = crypto.hash_password("Sup3r!Secret#Pass")
    assert crypto.verify_password("Sup3r!Secret#Pass", h) is True
    assert crypto.verify_password("wrong-password", h) is False


def test_derive_master_key_is_deterministic_per_salt():
    salt = crypto.generate_salt()
    k1 = crypto.derive_master_key("hunter2", salt)
    k2 = crypto.derive_master_key("hunter2", salt)
    assert k1 == k2
    assert len(k1) == crypto.AES_KEY_LEN


def test_derive_master_key_differs_across_salts():
    k1 = crypto.derive_master_key("hunter2", crypto.generate_salt())
    k2 = crypto.derive_master_key("hunter2", crypto.generate_salt())
    assert k1 != k2


def test_subkeys_are_independent_per_purpose():
    master = crypto.derive_master_key("hunter2", crypto.generate_salt())
    k_hmac = crypto.derive_subkey(master, "veil-integrity-hmac")
    k_chain = crypto.derive_subkey(master, "veil-audit-chain")
    assert k_hmac != k_chain
    assert k_hmac != master


def test_aes_gcm_encrypt_decrypt_roundtrip():
    key = crypto.derive_master_key("pw", crypto.generate_salt())
    plaintext = b"top secret payload \x00 with a NUL byte"
    blob = crypto.encrypt(plaintext, key, associated_data=b"entry-id")
    out = crypto.decrypt(blob, key, associated_data=b"entry-id")
    assert out == plaintext


def test_aes_gcm_rejects_tampered_ciphertext():
    key = crypto.derive_master_key("pw", crypto.generate_salt())
    blob = bytearray(crypto.encrypt(b"hello", key, associated_data=b"id"))
    blob[-1] ^= 0xFF  # flip a bit in the auth tag
    with pytest.raises(DecryptionError):
        crypto.decrypt(bytes(blob), key, associated_data=b"id")


def test_aes_gcm_rejects_wrong_associated_data():
    key = crypto.derive_master_key("pw", crypto.generate_salt())
    blob = crypto.encrypt(b"hello", key, associated_data=b"entry-a")
    with pytest.raises(DecryptionError):
        crypto.decrypt(blob, key, associated_data=b"entry-b")


def test_hmac_helpers():
    key = b"0" * 32
    h = crypto.hmac_sha256(key, b"data")
    assert crypto.verify_hmac(key, b"data", h) is True
    assert crypto.verify_hmac(key, b"tampered", h) is False
