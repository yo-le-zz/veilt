import time

import pytest

from veil.memory import create_engine, is_native_available


@pytest.fixture(params=["native"] + (["fallback"] if True else []))
def engine(request, monkeypatch):
    if request.param == "fallback":
        from veil import memory as memory_mod
        monkeypatch.setattr(memory_mod, "_NATIVE_AVAILABLE", False)
        return memory_mod.create_engine(max_access_per_window=5, min_interval_ms=20)
    return create_engine(max_access_per_window=5, min_interval_ms=20)


def test_native_engine_is_available():
    assert is_native_available() is True


def test_store_and_get_roundtrip(engine):
    engine.store("k", b"hello")
    assert engine.get("k") == b"hello"


def test_get_missing_key_returns_none(engine):
    assert engine.get("does-not-exist") is None


def test_embedded_nul_bytes_are_preserved(engine):
    data = b"AES-GCM-\x00\x00-CIPHERTEXT-AFTER-NUL"
    engine.store("k", data)
    assert engine.get("k") == data


def test_single_read_does_not_trigger_panic(engine):
    engine.store("k", b"data")
    assert engine.get("k") == b"data"
    assert engine.is_panic_mode() is False


def test_rapid_reaccess_triggers_panic(engine):
    engine.store("k", b"data")
    engine.get("k")
    second = engine.get("k")  # immediate re-access, well under min_interval_ms
    assert engine.is_panic_mode() is True
    assert second == engine.fake_dump()


def test_panic_mode_blocks_new_stores(engine):
    engine.force_panic()
    engine.store("new-key", b"value")
    assert engine.get("new-key") is None or engine.get("new-key") == engine.fake_dump()


def test_reset_panic(engine):
    engine.force_panic()
    assert engine.is_panic_mode() is True
    engine.reset_panic()
    assert engine.is_panic_mode() is False


def test_erase_entry(engine):
    engine.store("k", b"data")
    assert engine.erase_entry("k") is True
    assert engine.get("k") is None
    assert engine.erase_entry("k") is False  # already gone


def test_clear_all(engine):
    engine.store("a", b"1")
    engine.store("b", b"2")
    assert engine.size() == 2
    engine.clear_all()
    assert engine.size() == 0
    assert engine.is_panic_mode() is False


def test_slow_reads_do_not_trigger_panic(engine):
    engine.store("k", b"data")
    for _ in range(3):
        engine.get("k")
        time.sleep(0.03)  # comfortably above min_interval_ms=20
    assert engine.is_panic_mode() is False
