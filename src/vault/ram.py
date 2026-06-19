import ctypes
import os
import sys
from pathlib import Path

# Shared library name selection depending on the host platform
def get_shared_lib_name():
    if sys.platform == "win32":
        return "ram.dll"
    if sys.platform == "darwin":
        return "ram.dylib"
    return "ram.so"


# Shared library path detection
def get_ram_lib_path():
    lib_name = get_shared_lib_name()

    # Check if running from compiled executable
    if hasattr(sys, 'frozen'):
        if getattr(sys, '_MEIPASS', None):
            # PyInstaller one-file mode
            return Path(sys._MEIPASS) / lib_name
        else:
            # PyInstaller one-dir mode
            return Path(sys.executable).parent / lib_name

    # Development mode
    lib_paths = [
        Path(__file__).parent / "native" / "ram" / "build" / lib_name,
        Path(__file__).parent / "native" / "ram" / lib_name,
        Path.cwd() / lib_name,
    ]
    for path in lib_paths:
        if path.exists():
            return path

    return Path(lib_name)  # Fallback


# Use detected shared library path
dll_path = get_ram_lib_path()
ram = ctypes.CDLL(str(dll_path))

# =========================================================
# TYPES
# =========================================================
ram.store.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
ram.get.argtypes = [ctypes.c_char_p]
ram.get.restype = ctypes.c_char_p
ram.erase_entry.argtypes = [ctypes.c_char_p]
ram.clear_all.argtypes = []
ram.size.restype = ctypes.c_int
ram.fake_dump.restype = ctypes.c_char_p
ram.is_panic_mode.restype = ctypes.c_int

# =========================================================
# PYTHON WRAPPERS
# =========================================================

def store(id: bytes, data: bytes):
    ram.store(id, data, len(data))


def get(id: str):
    result = ram.get(id.encode())
    if result is None:
        return None
    # ctypes automatically converts c_char_p to Python bytes/str
    return result


def erase_entry(id: str):
    ram.erase_entry(id.encode())


def clear_all():
    ram.clear_all()


def size():
    return ram.size()


def fake_dump():
    return ram.fake_dump().decode()


def is_panic_mode():
    return ram.is_panic_mode() == 1