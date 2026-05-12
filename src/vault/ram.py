import ctypes
import os
import sys
from pathlib import Path

# DLL Path Detection
def get_dll_path():
    """Get RAM DLL path based on execution mode"""
    
    # Check if running from compiled executable
    if hasattr(sys, 'frozen'):
        if getattr(sys, '_MEIPASS', None):
            # PyInstaller one-file mode
            return Path(sys._MEIPASS) / "ram.dll"
        else:
            # PyInstaller one-dir mode
            return Path(sys.executable).parent / "ram.dll"
    else:
        # Development mode
        dll_paths = [
            Path(__file__).parent / "native" / "ram" / "build" / "ram.dll",
            Path(__file__).parent / "native" / "ram" / "ram.dll",
            Path.cwd() / "ram.dll"
        ]
        for path in dll_paths:
            if path.exists():
                return path
        return Path("ram.dll")  # Fallback

# Use detected DLL path
dll_path = get_dll_path()

ram = ctypes.CDLL(dll_path)

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