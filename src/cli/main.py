"""
veil.cli.main
===============
The `veil` command-line tool. A thin, FR/EN-aware layer on top of
veil.vault.Vault - every command here is also directly available as a
Python API call (see the README "Library usage" section).
"""
from __future__ import annotations

import getpass
import sys
from typing import Optional

import typer

from .. import i18n
from ..elevate import is_admin, request_admin
from ..exceptions import VeilError
from ..vault import Vault
from . import output as out

app = typer.Typer(
    name="veil",
    help="VEIL - Secure encrypted vault (in-memory + on-disk), usable as a CLI or a Python library.",
    add_completion=True,
    no_args_is_help=True,
)
config_app = typer.Typer(help="Manage vault configuration.")
audit_app = typer.Typer(help="Inspect and verify the tamper-evident audit log.")
app.add_typer(config_app, name="config")
app.add_typer(audit_app, name="audit")


def _prompt_password(prompt_text: str = "Master password: ") -> str:
    return getpass.getpass(prompt_text)


def _resolve_password(password: Optional[str]) -> str:
    if password:
        out.warning(
            "Passing --password on the command line is visible in your shell "
            "history and process list. Prefer the interactive prompt or the "
            "VEIL_PASSWORD environment variable for scripts."
        )
        return password
    import os
    env_pw = os.environ.get("VEIL_PASSWORD")
    if env_pw:
        return env_pw
    return _prompt_password()


def _open_vault(name: str, password: str, storage: str, admin: bool) -> Vault:
    try:
        return Vault(password=password, name=name, storage=storage, admin=admin)
    except VeilError as exc:
        out.error(str(exc))
        raise typer.Exit(code=1)
    except ValueError as exc:
        out.error(i18n.t("weak_password", reason=str(exc)))
        raise typer.Exit(code=1)


@app.callback()
def main_callback(
    ctx: typer.Context,
    lang: str = typer.Option("fr", "--lang", help="Interface language: fr | en"),
    admin: bool = typer.Option(
        False, "--admin",
        help="Request administrator/root privileges for this command before running it "
             "(stronger memory locking, system-wide storage). Triggers a UAC/sudo prompt.",
    ),
):
    i18n.set_language(lang)
    if admin and not is_admin():
        out.info(i18n.t("elevation_requested"))
        request_admin()  # relaunches elevated and exits this process
    ctx.obj = {"admin": admin}


@app.command()
def version() -> None:
    """Print the VEIL version."""
    from .._version import VERSION
    out.console.print(f"VEIL v{VERSION}")


# ===================================================================
# CONFIG
# ===================================================================
@config_app.command("init")
def config_init(
    ctx: typer.Context,
    name: str = typer.Option("default", "--name", help="Vault name"),
    storage: str = typer.Option("ram", "--storage", help="ram | disk"),
    password: Optional[str] = typer.Option(None, "--password", help="Master password (insecure on shared machines)"),
    no_hmac: bool = typer.Option(False, "--no-hmac", help="Disable the extra HMAC integrity layer"),
) -> None:
    """Initialize a new vault."""
    pw = _resolve_password(password)
    admin = ctx.obj.get("admin", False) if ctx.obj else False
    try:
        vault = Vault(password=pw, name=name, storage=storage, admin=admin, hmac_enabled=not no_hmac)
    except ValueError as exc:
        out.error(i18n.t("weak_password", reason=str(exc)))
        raise typer.Exit(code=1)
    out.success(i18n.t("vault_initialized", name=name))
    vault.close()


@config_app.command("show")
def config_show(
    ctx: typer.Context,
    name: str = typer.Option("default", "--name"),
    password: Optional[str] = typer.Option(None, "--password"),
) -> None:
    """Show vault status and configuration."""
    pw = _resolve_password(password)
    admin = ctx.obj.get("admin", False) if ctx.obj else False
    vault = _open_vault(name, pw, "ram", admin)
    out.print_status(vault.status(), title=f"veil config — {name}")
    vault.close()


# ===================================================================
# SECRETS CRUD
# ===================================================================
@app.command()
def add(
    ctx: typer.Context,
    entry_id: str = typer.Argument(..., metavar="ID"),
    value: Optional[str] = typer.Argument(None, metavar="VALUE"),
    name: str = typer.Option("default", "--name"),
    storage: str = typer.Option("ram", "--storage"),
    password: Optional[str] = typer.Option(None, "--password"),
    ttl: Optional[float] = typer.Option(None, "--ttl", help="Auto-delete after N seconds"),
) -> None:
    """Encrypt and store a secret. Prompts for VALUE if omitted (hidden input)."""
    if value is None:
        value = getpass.getpass(f"Value for '{entry_id}': ")
    pw = _resolve_password(password)
    admin = ctx.obj.get("admin", False) if ctx.obj else False
    vault = _open_vault(name, pw, storage, admin)
    try:
        vault.set(entry_id, value, ttl=ttl)
        out.success(i18n.t("entry_added", id=entry_id))
    except VeilError as exc:
        out.error(str(exc))
        raise typer.Exit(code=1)
    finally:
        vault.close()


@app.command(name="set")
def set_command(
    ctx: typer.Context,
    entry_id: str = typer.Argument(..., metavar="ID"),
    value: Optional[str] = typer.Argument(None, metavar="VALUE"),
    name: str = typer.Option("default", "--name"),
    storage: str = typer.Option("ram", "--storage"),
    password: Optional[str] = typer.Option(None, "--password"),
    ttl: Optional[float] = typer.Option(None, "--ttl", help="Auto-delete after N seconds"),
) -> None:
    """Alias for 'add'."""
    add(ctx, entry_id, value, name, storage, password, ttl)


@app.command()
def get(
    ctx: typer.Context,
    entry_id: str = typer.Argument(..., metavar="ID"),
    name: str = typer.Option("default", "--name"),
    storage: str = typer.Option("ram", "--storage"),
    password: Optional[str] = typer.Option(None, "--password"),
) -> None:
    """Decrypt and print a stored secret."""
    pw = _resolve_password(password)
    admin = ctx.obj.get("admin", False) if ctx.obj else False
    vault = _open_vault(name, pw, storage, admin)
    try:
        value = vault.get(entry_id)
        out.console.print(value)
    except VeilError as exc:
        if vault.is_panic:
            out.error(i18n.t("panic_mode_active"))
        else:
            out.error(i18n.t("entry_not_found", id=entry_id))
        raise typer.Exit(code=1)
    finally:
        vault.close()


@app.command(name="del")
def delete(
    ctx: typer.Context,
    entry_id: str = typer.Argument(..., metavar="ID"),
    name: str = typer.Option("default", "--name"),
    storage: str = typer.Option("ram", "--storage"),
    password: Optional[str] = typer.Option(None, "--password"),
) -> None:
    """Securely delete a stored secret."""
    pw = _resolve_password(password)
    admin = ctx.obj.get("admin", False) if ctx.obj else False
    vault = _open_vault(name, pw, storage, admin)
    try:
        existed = vault.delete(entry_id)
        if existed:
            out.success(i18n.t("entry_deleted", id=entry_id))
        else:
            out.error(i18n.t("entry_not_found", id=entry_id))
            raise typer.Exit(code=1)
    finally:
        vault.close()


@app.command()
def see(
    ctx: typer.Context,
    name: str = typer.Option("default", "--name"),
    storage: str = typer.Option("ram", "--storage"),
    password: Optional[str] = typer.Option(None, "--password"),
) -> None:
    """List every entry in the vault (metadata only, never decrypted)."""
    pw = _resolve_password(password)
    admin = ctx.obj.get("admin", False) if ctx.obj else False
    vault = _open_vault(name, pw, storage, admin)
    entries = vault.list_entries()
    if entries:
        out.print_entries(entries)
    else:
        out.info("No entries." if i18n.get_language() == "en" else "Aucune entrée.")
    vault.close()


@app.command()
def integrity(
    ctx: typer.Context,
    entry_id: str = typer.Argument(..., metavar="ID"),
    name: str = typer.Option("default", "--name"),
    storage: str = typer.Option("ram", "--storage"),
    password: Optional[str] = typer.Option(None, "--password"),
) -> None:
    """Verify the integrity of a single entry without printing its value."""
    pw = _resolve_password(password)
    admin = ctx.obj.get("admin", False) if ctx.obj else False
    vault = _open_vault(name, pw, storage, admin)
    try:
        vault.get(entry_id)
        out.success(i18n.t("integrity_ok", id=entry_id))
    except VeilError:
        out.error(i18n.t("integrity_failed", id=entry_id))
        raise typer.Exit(code=1)
    finally:
        vault.close()


@app.command("reset-panic")
def reset_panic(
    ctx: typer.Context,
    name: str = typer.Option("default", "--name"),
    storage: str = typer.Option("ram", "--storage"),
    password: Optional[str] = typer.Option(None, "--password"),
) -> None:
    """Explicitly re-arm a vault after a panic-mode trigger you've reviewed."""
    pw = _resolve_password(password)
    admin = ctx.obj.get("admin", False) if ctx.obj else False
    vault = _open_vault(name, pw, storage, admin)
    vault.reset_panic()
    out.success(i18n.t("panic_mode_reset", name=name))
    vault.close()


@app.command()
def purge(
    name: str = typer.Option("default", "--name"),
    yes: bool = typer.Option(False, "--yes", help="Confirm irreversible deletion"),
) -> None:
    """Irreversibly wipe a vault: every entry, config, and audit log."""
    if not yes:
        out.warning(i18n.t("purge_confirm", name=name))
        raise typer.Exit(code=1)
    # purge() needs the vault to exist & be unlocked first for a clean,
    # audited wipe, but if the password was lost the directory is just
    # removed directly.
    from .. import config as cfgmod
    import shutil
    data_dir = cfgmod.get_data_dir() / name
    if data_dir.exists():
        shutil.rmtree(data_dir, ignore_errors=True)
    out.success(i18n.t("purge_complete", name=name))


# ===================================================================
# AUDIT LOG
# ===================================================================
@audit_app.command("verify")
def audit_verify(
    ctx: typer.Context,
    name: str = typer.Option("default", "--name"),
    storage: str = typer.Option("ram", "--storage"),
    password: Optional[str] = typer.Option(None, "--password"),
) -> None:
    """Verify the audit log's tamper-evident hash chain."""
    pw = _resolve_password(password)
    admin = ctx.obj.get("admin", False) if ctx.obj else False
    vault = _open_vault(name, pw, storage, admin)
    if vault.verify_audit_log():
        out.success(i18n.t("audit_chain_valid"))
    else:
        out.error(i18n.t("audit_chain_broken"))
        raise typer.Exit(code=1)
    vault.close()


@audit_app.command("show")
def audit_show(
    ctx: typer.Context,
    name: str = typer.Option("default", "--name"),
    storage: str = typer.Option("ram", "--storage"),
    password: Optional[str] = typer.Option(None, "--password"),
    limit: int = typer.Option(20, "--limit"),
) -> None:
    """Show the most recent audit log events."""
    pw = _resolve_password(password)
    admin = ctx.obj.get("admin", False) if ctx.obj else False
    vault = _open_vault(name, pw, storage, admin)
    for event in vault.audit_events(limit=limit):
        out.console.print(
            f"[dim]{event.get('timestamp')}[/dim] "
            f"[bold]{event.get('event_type')}[/bold] "
            f"{event.get('entry_id') or ''} {event.get('reason') or ''}"
        )
    vault.close()


def run() -> None:
    try:
        app()
    except KeyboardInterrupt:
        out.error("Interrupted.")
        sys.exit(130)


if __name__ == "__main__":
    run()
