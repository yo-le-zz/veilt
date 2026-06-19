from veilt import crypto, integrity


def test_compute_and_verify_entry_hash():
    key = crypto.derive_subkey(b"0" * 32, "test-purpose")
    ciphertext = b"some-ciphertext-bytes"
    h = integrity.compute_entry_hash("entry-1", ciphertext, key)
    assert integrity.verify_entry_hash("entry-1", ciphertext, key, h) is True


def test_verify_fails_on_tampered_ciphertext():
    key = crypto.derive_subkey(b"0" * 32, "test-purpose")
    ciphertext = b"some-ciphertext-bytes"
    h = integrity.compute_entry_hash("entry-1", ciphertext, key)
    tampered = b"some-ciphertext-bytfs"
    assert integrity.verify_entry_hash("entry-1", tampered, key, h) is False


def test_verify_fails_on_wrong_entry_id():
    key = crypto.derive_subkey(b"0" * 32, "test-purpose")
    ciphertext = b"some-ciphertext-bytes"
    h = integrity.compute_entry_hash("entry-1", ciphertext, key)
    assert integrity.verify_entry_hash("entry-2", ciphertext, key, h) is False
