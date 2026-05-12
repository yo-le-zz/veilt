import json
import os
import hashlib

from config import CONFIG_TEMPLATE, config_path

CONFIG = None
MASTER_HASH = None


# =========================================================
# VALIDATION
# =========================================================

def validate_storage(storage: str):
    if storage not in ["ram", "disk"]:
        raise ValueError("storage must be 'ram' or 'disk'")


def validate_password(password: str):
    if not password or password.strip() == "":
        raise ValueError("password cannot be empty")

    if password == ".":
        raise ValueError("invalid password")

    if len(password) < 4:
        raise ValueError("password too short (min 4)")

# =========================================================
# Parser la ram et les gigaoctets
# =========================================================

def parse_size(value):
    if value is None:
        return "unlimited"

    if value.isdigit():
        return int(value)

    value = value.lower()

    if value.endswith("mo"):
        return int(value.replace("mo", "")) * 1
    if value.endswith("gb"):
        return int(value.replace("gb", "")) * 1024

    raise ValueError("Invalid size format (use 100, 100mo, 1gb)")

# =========================================================
# INIT CONFIG (obligatoire première fois)
# =========================================================

def init_config(storage: str, password: str, ram_limit=None, disk_limit=None):
    global CONFIG, MASTER_HASH

    validate_storage(storage)
    validate_password(password)

    ram_limit = parse_size(ram_limit)
    disk_limit = parse_size(disk_limit)

    MASTER_HASH = hashlib.sha256(password.encode()).hexdigest()

    CONFIG = CONFIG_TEMPLATE.copy()
    CONFIG.update({
        "storage": storage,
        "ram_limit": ram_limit,
        "disk_limit": disk_limit,
        "password": MASTER_HASH
    })

    save_config()
    return CONFIG


# =========================================================
# SET CONFIG (modification)
# =========================================================

def set_config(storage=None, password=None, ram_limit=None, disk_limit=None):
    global CONFIG

    if CONFIG is None:
        raise Exception("Config not initialized. Run init first.")

    if storage is not None:
        validate_storage(storage)
        CONFIG["storage"] = storage

    if password is not None:
        validate_password(password)
        CONFIG["password"] = hashlib.sha256(password.encode()).hexdigest()

    if ram_limit is not None:
        CONFIG["ram_limit"] = ram_limit

    if disk_limit is not None:
        CONFIG["disk_limit"] = disk_limit

    save_config()
    return CONFIG


# =========================================================
# GET CONFIG
# =========================================================

def get_config():
    if CONFIG is None:
        return {
            "status": "not_initialized",
            "message": "Run: veil config init"
        }

    return CONFIG


# =========================================================
# SAVE CONFIG
# =========================================================

def save_config():
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(CONFIG, f, indent=2)