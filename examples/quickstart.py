"""
VEIL quickstart - run with:  python examples/quickstart.py
"""
import veil

# 1. Library usage: in-memory vault, password only.
with veil.Vault(password="Example-P@ssw0rd!1") as vault:
    vault.set("api_key", "sk-example-123456")
    print("Retrieved:", vault.get("api_key"))
    print("Status:", vault.status())

# 2. Disk-backed vault: secrets persist (encrypted) across process restarts.
with veil.Vault(password="Example-P@ssw0rd!1", name="persistent", storage="disk") as vault:
    vault.set("db_password", "s3cr3t", ttl=120)  # auto-deleted after 2 minutes
    print("DB password:", vault.get("db_password"))

# 3. One-liners, keyring-style.
veil.quick_set("token", "ghp_example", password="Example-P@ssw0rd!1", vault_name="oneliner")
print("Quick get:", veil.quick_get("token", password="Example-P@ssw0rd!1", vault_name="oneliner"))

# Clean up the example vaults so re-running this script stays idempotent.
for name in ("default", "persistent", "oneliner"):
    try:
        with veil.Vault(password="Example-P@ssw0rd!1", name=name) as v:
            v.purge()
    except veil.VeilError:
        pass
