# =========================================================
# App version
# =========================================================
VERSION = "1.0.0"

# =========================================================
# Commands and descriptions
# =========================================================
COMMANDS = {
    "help": "Display commands information",
    "version": "Display version information",
    "config": "Manage configuration (init / get / set)",
    "add": "Add encrypted data to vault (txt/file)",
    "get": "Retrieve and decrypt data from vault",
    "del": "Securely delete entry from vault",
    "see": "Show vault status and entry information",
    "integrity": "Check system and data integrity",
    "purge": "Complete cleanup of VEIL system"
}

config_path = "datas/config.json"

CONFIG_TEMPLATE = {
    "storage": None,        # "ram" ou "disk"
    "ram_limit": None,      # int (MB)
    "disk_limit": None,     # int (MB ou KB selon ton choix)
    
    "password_hash": None,  # hash SHA256 du password principal
    "salt": None,           # salt PUBLIC
    
    "initialized": False    # évite re-init accidentel
}