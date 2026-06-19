import pytest

import veilt
from veilt.exceptions import (
    AuthenticationError,
    EntryNotFoundError,
    PanicModeError,
)


PW = "Tr0ub4dor!&3Correct"


def test_create_and_unlock_vault():
    with veilt.Vault(password=PW, name="v1", storage="ram") as v:
        assert v.status()["sealed"] is False
    # status persisted, password re-verifies on reopen
    with veilt.Vault(password=PW, name="v1", storage="ram") as v2:
        assert v2.status()["sealed"] is False


def test_wrong_password_rejected():
    with veilt.Vault(password=PW, name="v2", storage="ram"):
        pass
    with pytest.raises(AuthenticationError):
        veilt.Vault(password="totally-wrong-password", name="v2", storage="ram")


def test_set_get_roundtrip_ram():
    with veilt.Vault(password=PW, name="v3", storage="ram") as v:
        v.set("api_key", "sk-abcdef123456")
        assert v.get("api_key") == "sk-abcdef123456"


def test_get_missing_entry_raises():
    with veilt.Vault(password=PW, name="v4", storage="ram") as v:
        with pytest.raises(EntryNotFoundError):
            v.get("nope")


def test_get_missing_entry_with_default():
    with veilt.Vault(password=PW, name="v5", storage="ram") as v:
        assert v.get("nope", default="fallback") == "fallback"


def test_delete_entry():
    with veilt.Vault(password=PW, name="v6", storage="ram") as v:
        v.set("a", "1")
        assert v.delete("a") is True
        assert v.delete("a") is False
        with pytest.raises(EntryNotFoundError):
            v.get("a")


def test_disk_storage_persists_across_instances():
    with veilt.Vault(password=PW, name="v7", storage="disk") as v:
        v.set("persisted", "value-123")
    with veilt.Vault(password=PW, name="v7", storage="disk") as v2:
        assert v2.get("persisted") == "value-123"


def test_seal_wipes_master_key():
    v = veilt.Vault(password=PW, name="v8", storage="ram")
    v.set("a", "1")
    v.close()
    with pytest.raises(veilt.VeilError):
        v.get("a")


def test_panic_mode_raises_and_can_be_reset():
    with veilt.Vault(password=PW, name="v9", storage="ram", min_access_interval_ms=50) as v:
        v.set("k", "value")
        v.get("k")
        with pytest.raises(PanicModeError):
            v.get("k")  # immediate re-access
        assert v.is_panic is True
        v.reset_panic()
        assert v.is_panic is False


def test_audit_log_records_events_and_chain_is_valid():
    with veilt.Vault(password=PW, name="v10", storage="ram") as v:
        v.set("a", "1")
        v.get("a")
        v.delete("a")
        assert v.verify_audit_log() is True
        events = v.audit_events(limit=10)
        event_types = {e["event_type"] for e in events}
        assert "ENTRY_CREATED" in event_types
        assert "ENTRY_ACCESSED" in event_types
        assert "ENTRY_DELETED" in event_types


def test_list_entries():
    with veilt.Vault(password=PW, name="v11", storage="ram") as v:
        v.set("x", "1")
        v.set("y", "2")
        ids = {e["id"] for e in v.list_entries()}
        assert ids == {"x", "y"}


def test_quick_set_get_helpers():
    veilt.quick_set("token", "ghp_xxx", password=PW, vault_name="v12", storage="disk")
    assert veilt.quick_get("token", password=PW, vault_name="v12", storage="disk") == "ghp_xxx"


def test_weak_password_rejected_on_new_vault():
    with pytest.raises(ValueError):
        veilt.Vault(password="abc", name="v13", storage="ram")


def test_purge_removes_everything():
    with veilt.Vault(password=PW, name="v14", storage="disk") as v:
        v.set("x", "1")
        data_dir = v._data_dir
        v.purge()
    assert not data_dir.exists()
