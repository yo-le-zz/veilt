"""
veil.config
============
Cross-platform secure storage locations.

  - Linux/macOS (per-user) : $XDG_DATA_HOME/veil  or  ~/.local/share/veil
  - Windows (per-user)     : %LOCALAPPDATA%\\Veil
  - Linux (admin/root)     : /etc/veil
  - Windows (admin)        : %PROGRAMDATA%\\Veil

This fixes a real-world packaging bug class (e.g. trying to write to a
fixed path like /opt/<app>/data with no write permission for a normal
user): VEIL always resolves a writable, per-user location by default,
and only ever touches a system-wide location when the caller explicitly
runs elevated.
"""
from __future__ import annotations

import json
import os
import platform
import stat
from pathlib import Path
from typing import Optional

from .exceptions import ConfigError
from ._version import VERSION

APP_NAME = "veil"
CONFIG_FILENAME = "config.json"

CONFIG_TEMPLATE = {
    "version": VERSION,
    "storage": None,          # "ram" | "disk"
    "ram_limit": None,         # int (MB) or None = unlimited
    "disk_limit": None,        # int (MB) or None = unlimited
    "password_hash": None,     # Argon2id encoded hash (salt + params included)
    "salt": None,               # hex-encoded salt used for key derivation
    "hmac_enabled": True,
    "language": "fr",
    "initialized": False,
}


def get_user_data_dir() -> Path:
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "Veil"
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / APP_NAME


def get_system_data_dir() -> Path:
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
        return Path(base) / "Veil"
    return Path("/etc") / APP_NAME


def get_data_dir(use_system: bool = False) -> Path:
    """Return (and create, with restrictive permissions) the base VEIL
    data directory for the requested scope."""
    path = get_system_data_dir() if use_system else get_user_data_dir()
    path.mkdir(parents=True, exist_ok=True)
    _secure_permissions(path)
    return path


def _secure_permissions(path: Path) -> None:
    """Best-effort: restrict a directory to owner-only access."""
    try:
        if platform.system() != "Windows":
            os.chmod(path, stat.S_IRWXU)  # rwx for owner only (0700)
    except OSError:
        pass


def load_config_at(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        raise ConfigError(f"Corrupted configuration file at {path}: {exc}") from exc


def save_config_at(config: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    tmp_path.replace(path)  # atomic rename on both POSIX and Windows
    try:
        if platform.system() != "Windows":
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0600
    except OSError:
        pass
