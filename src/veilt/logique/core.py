from config import CONFIG_TEMPLATE, config_path
from vault.crypto import hash_password, derive_master_key, generate_salt
from cryptography.fernet import Fernet
from vault.daemon import INDEX
from vault.ram import ram
import tempfile
import os
import json

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
        
    # Mot de passe trop court
    if len(password) < 8:
        raise ValueError("password too short (min 8 characters)")
    
    # Mots de passe faibles connus
    weak_passwords = [
        "password", "12345678", "qwerty", "abc12345", "password123",
        "admin", "letmein", "welcome", "monkey", "dragon",
        "master", "sunshine", "iloveyou", "football"
    ]
    
    if password.lower() in weak_passwords:
        raise ValueError("password is too common and weak")
    
    # Vérifier la complexité
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    
    complexity_score = sum([has_upper, has_lower, has_digit, has_special])
    
    if complexity_score < 3:
        raise ValueError("password must contain at least 3 of: uppercase, lowercase, digits, special characters")

# =========================================================
# Parser la ram et les gigaoctets
# =========================================================

def parse_size(value):
    if value is None:
        return "unlimited"

    value = str(value).lower().strip()

    if value.isdigit():
        return int(value)

    if value.endswith("mo"):
        return int(value[:-2])
    if value.endswith("gb"):
        return int(value[:-2]) * 1024

    raise ValueError("Invalid size format (use 100, 100mo, 1gb)")

# =========================================================
# INIT CONFIG (obligatoire première fois)
# =========================================================

def init_config(storage: str, password: str, ram_limit=None, disk_limit=None):
    global CONFIG, MASTER_KEY

    validate_storage(storage)
    validate_password(password)

    ram_limit = parse_size(ram_limit)
    disk_limit = parse_size(disk_limit)

    # =========================
    # CRYPTO LAYER CALLS
    # =========================
    password_hash = hash_password(password)
    salt = generate_salt()
    MASTER_KEY = derive_master_key(password, salt)

    # =========================
    # CONFIG BUILD
    # =========================
    CONFIG = CONFIG_TEMPLATE.copy()
    CONFIG.update({
        "storage": storage,
        "ram_limit": ram_limit,
        "disk_limit": disk_limit,
        "password_hash": password_hash,
        "salt": salt,
        "initialized": True
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
        CONFIG["password_hash"] = hash_password(password)

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
    global CONFIG

    if CONFIG is None:
        load_config()

    if CONFIG is None:
        return {
            "status": "not_initialized",
            "message": "Run: veilt config init"
        }

    return CONFIG

# =========================================================
# LOAD CONFIG
# =========================================================

def load_config():
    global CONFIG

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            CONFIG = json.load(f)
    except:
        CONFIG = None


# =========================================================
# SAVE CONFIG
# =========================================================

def save_config():
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(CONFIG, f, indent=2)
        

# =========================================================
# CHECK PASSWORD
# =========================================================

def check_password(password: str) -> bool:
    if CONFIG is None:
        raise Exception("Config not initialized")

    stored = CONFIG.get("password_hash")
    if not stored:
        raise Exception("Password hash missing")

    return hash_password(password) == stored

# =========================================================
# AUTHENTICATION
# =========================================================

def authenticate(password: str):
    """
    Vérifie mot de passe + dérive master key
    """
    
    global CONFIG
    load_config()

    if CONFIG is None:
        raise Exception("Config not initialized")

    if hash_password(password) != CONFIG["password_hash"]:
        raise Exception("Invalid password")

    return derive_master_key(password, CONFIG["salt"])

# =========================================================
# ADD DATA 
# =========================================================

def add_data(password: str, id: str, data: str):

    global CONFIG
    load_config()  # 🔥 IMPORTANT

    if CONFIG is None:
        raise Exception("Config not initialized")

    master_key = authenticate(password)

    storage = CONFIG["storage"]

    # =========================================================
    # ENCRYPT DATA
    # =========================================================
    f = Fernet(master_key.encode())
    encrypted_data = f.encrypt(data.encode())

    # =========================================================
    # RAM MODE
    # =========================================================
    if storage == "ram":

        ram.store(
            id.encode(),
            encrypted_data
        )

        INDEX[id] = {"type": "ram"}

        return {"status": "stored_in_ram", "id": id}

    # =========================================================
    # DISK MODE
    # =========================================================
    elif storage == "disk":

        tmp_dir = os.path.join(tempfile.gettempdir(), "veilt_vault")
        os.makedirs(tmp_dir, exist_ok=True)

        file_path = os.path.join(tmp_dir, f"{id}.veilt")

        with open(file_path, "wb") as f:
            f.write(encrypted_data)

        INDEX[id] = {
            "type": "disk",
            "path": file_path
        }

        return {"status": "stored_in_disk", "id": id}