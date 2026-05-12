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
    "config": "Manage configuration (init / get / set)"
}

config_path = "datas/config.json"
CONFIG_TEMPLATE = {
    "storage": None,
    "ram_limit": None,
    "disk_limit": None,
    "password": None
}