"""
veil.osvault
=============
Optional integration with the operating system's own secret store -
inspired by Windows Credential Manager, macOS Keychain, and the
`keyring` library, WITHOUT reimplementing any of them as a server.

IMPORTANT: this module never stores your vault's master password or
your secrets in plaintext here. It only optionally stores a small
"quick-unlock token" (itself just another VEIL-encrypted blob) so a
trusted, already-logged-in OS session can skip retyping the master
password - exactly the convenience trade-off Windows Credential Manager
/ Keychain / keyring make, applied on top of (not instead of) VEIL's
own encryption.

Backends:
  - Windows : native, zero-extra-dependency bindings to the real
              Credential Manager (advapi32 CredWriteW/CredReadW/
              CredDeleteW) via ctypes.
  - Linux/macOS : delegates to the optional `keyring` package (Secret
              Service / KWallet / Keychain), installed with
              `pip install veil-vault[keyring]`. Not a hard dependency:
              headless Linux servers (e.g. your Ubuntu box) simply
              won't have this feature available, which is expected.
"""
from __future__ import annotations

import platform
from typing import Optional

from .exceptions import VeilError

_SERVICE_PREFIX = "veil-vault"


# =========================================================
# WINDOWS NATIVE BACKEND (no extra dependency required)
# =========================================================
def _windows_backend():
    import ctypes
    import ctypes.wintypes as wt

    CRED_TYPE_GENERIC = 1
    CRED_PERSIST_LOCAL_MACHINE = 2

    class CREDENTIAL(ctypes.Structure):
        _fields_ = [
            ("Flags", wt.DWORD),
            ("Type", wt.DWORD),
            ("TargetName", wt.LPWSTR),
            ("Comment", wt.LPWSTR),
            ("LastWritten", wt.FILETIME),
            ("CredentialBlobSize", wt.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
            ("Persist", wt.DWORD),
            ("AttributeCount", wt.DWORD),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wt.LPWSTR),
            ("UserName", wt.LPWSTR),
        ]

    advapi32 = ctypes.windll.advapi32  # type: ignore[attr-defined]

    def write(target: str, secret: bytes) -> None:
        blob_buf = ctypes.create_string_buffer(secret, len(secret))
        cred = CREDENTIAL()
        cred.Flags = 0
        cred.Type = CRED_TYPE_GENERIC
        cred.TargetName = target
        cred.Comment = "Managed by VEIL"
        cred.CredentialBlobSize = len(secret)
        cred.CredentialBlob = ctypes.cast(blob_buf, ctypes.POINTER(ctypes.c_byte))
        cred.Persist = CRED_PERSIST_LOCAL_MACHINE
        cred.UserName = "veil"
        if not advapi32.CredWriteW(ctypes.byref(cred), 0):
            raise VeilError(f"CredWriteW failed (Win32 error {ctypes.GetLastError()})")

    def read(target: str) -> Optional[bytes]:
        p_cred = ctypes.POINTER(CREDENTIAL)()
        if not advapi32.CredReadW(target, CRED_TYPE_GENERIC, 0, ctypes.byref(p_cred)):
            return None
        try:
            cred = p_cred.contents
            size = cred.CredentialBlobSize
            if size == 0:
                return b""
            buf_type = ctypes.c_byte * size
            buf = ctypes.cast(cred.CredentialBlob, ctypes.POINTER(buf_type)).contents
            return bytes(bytearray(buf))
        finally:
            advapi32.CredFree(p_cred)

    def delete(target: str) -> None:
        advapi32.CredDeleteW(target, CRED_TYPE_GENERIC, 0)

    return write, read, delete


# =========================================================
# KEYRING BACKEND (optional dependency, cross-platform)
# =========================================================
def _keyring_backend():
    try:
        import keyring  # type: ignore
    except ImportError as exc:
        raise VeilError(
            "The optional 'keyring' dependency is not installed. "
            "Install it with: pip install veil-vault[keyring]"
        ) from exc

    def write(target: str, secret: bytes) -> None:
        keyring.set_password(_SERVICE_PREFIX, target, secret.hex())

    def read(target: str) -> Optional[bytes]:
        value = keyring.get_password(_SERVICE_PREFIX, target)
        return bytes.fromhex(value) if value is not None else None

    def delete(target: str) -> None:
        try:
            keyring.delete_password(_SERVICE_PREFIX, target)
        except Exception:
            pass

    return write, read, delete


def is_available() -> bool:
    if platform.system() == "Windows":
        return True  # native backend, always available on Windows
    try:
        _keyring_backend()
        return True
    except VeilError:
        return False


def _backend():
    if platform.system() == "Windows":
        return _windows_backend()
    return _keyring_backend()


def store_unlock_token(vault_name: str, token: str) -> None:
    """Store a wrapped quick-unlock token in the OS-native secret store."""
    write, _, _ = _backend()
    write(f"{_SERVICE_PREFIX}:{vault_name}", token.encode("utf-8"))


def get_unlock_token(vault_name: str) -> Optional[str]:
    _, read, _ = _backend()
    result = read(f"{_SERVICE_PREFIX}:{vault_name}")
    return result.decode("utf-8") if result is not None else None


def delete_unlock_token(vault_name: str) -> None:
    _, _, delete = _backend()
    delete(f"{_SERVICE_PREFIX}:{vault_name}")
