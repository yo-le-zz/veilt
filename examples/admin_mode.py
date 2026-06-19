"""
VEIL admin/elevated mode example.

Run normally first - it will explain what --admin/admin=True unlocks
without forcing elevation on you. Re-run with `python examples/admin_mode.py
--elevate` to actually request a UAC/sudo prompt.
"""
import sys

import veil
from veil import elevate

print("Currently running as admin/root:", elevate.is_admin())

if "--elevate" in sys.argv and not elevate.is_admin():
    print("Requesting elevated privileges (this will prompt you)...")
    elevate.request_admin()  # relaunches elevated and exits this process

with veil.Vault(
    password="Admin-Example-P@ss!1",
    name="admin-demo",
    storage="disk",
    admin=elevate.is_admin(),
) as vault:
    vault.set("secret", "only-you-should-see-this")
    status = vault.status()
    print("Vault status:", status)
    print("Running elevated:", status["admin"])
    vault.purge()
