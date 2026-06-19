"""
veilt.elevate
=============
Detect and (only when explicitly asked) request administrator/root
privileges.

VEIL never elevates itself silently - elevation is always an explicit,
opt-in call from your own code (or the `--admin` CLI flag). Running
elevated unlocks extra hardening in Vault:

    - Unrestricted memory locking (mlock/VirtualLock without the small
      default quota unprivileged processes get).
    - Stronger anti-debug / anti-dump process mitigations.
    - A system-wide secure storage location instead of the per-user one.
"""
from __future__ import annotations

import ctypes
import os
import platform
import subprocess
import sys
from typing import List, Optional

from .exceptions import ElevationError


def is_admin() -> bool:
    """Return True if the current process already has administrator
    (Windows) or root (Linux/macOS) privileges."""
    system = platform.system()
    try:
        if system == "Windows":
            return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
        return os.geteuid() == 0
    except Exception:
        return False


def request_admin(argv: Optional[List[str]] = None) -> None:
    """
    Relaunch the current process with elevated privileges and exit the
    current (unprivileged) one. No-op if already elevated.

    Windows : prompts a UAC consent dialog (ShellExecute "runas").
    Linux   : tries `pkexec` (graphical prompt) then falls back to `sudo`.
    """
    if is_admin():
        return

    system = platform.system()
    argv = list(argv) if argv is not None else sys.argv[:]

    try:
        if system == "Windows":
            params = " ".join(f'"{a}"' for a in argv)
            result = ctypes.windll.shell32.ShellExecuteW(  # type: ignore[attr-defined]
                None, "runas", sys.executable, params, None, 1
            )
            if int(result) <= 32:
                raise ElevationError(
                    f"Windows refused the elevation request (ShellExecute code {result})"
                )
        else:
            for elevator in ("pkexec", "sudo"):
                try:
                    subprocess.run([elevator, sys.executable, *argv], check=True)
                    break
                except FileNotFoundError:
                    continue
            else:
                raise ElevationError("Neither 'pkexec' nor 'sudo' is available on this system")
    except ElevationError:
        raise
    except Exception as exc:
        raise ElevationError(f"Failed to request elevated privileges: {exc}") from exc

    sys.exit(0)


def harden_token_privileges() -> bool:
    """
    Windows-only: enable SeLockMemoryPrivilege and SeIncreaseWorkingSetPrivilege
    on the current process token, so VirtualLock can pin much larger regions
    than the small default working-set quota allows.

    Requires the optional `pywin32` dependency (pip install veilt[windows]).
    Safe no-op everywhere else, or if pywin32 isn't installed / the privilege
    isn't granted to this account.
    """
    if platform.system() != "Windows":
        return False

    try:
        import win32api  # type: ignore
        import win32security  # type: ignore
    except ImportError:
        return False

    ok = True
    for priv_name in ("SeLockMemoryPrivilege", "SeIncreaseWorkingSetPrivilege"):
        try:
            h_token = win32security.OpenProcessToken(
                win32api.GetCurrentProcess(),
                win32security.TOKEN_ADJUST_PRIVILEGES | win32security.TOKEN_QUERY,
            )
            priv_id = win32security.LookupPrivilegeValue(None, priv_name)
            win32security.AdjustTokenPrivileges(
                h_token, False, [(priv_id, win32security.SE_PRIVILEGE_ENABLED)]
            )
        except Exception:
            ok = False
    return ok
