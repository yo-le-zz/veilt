import hashlib
import secrets
import base64
from cryptography.fernet import Fernet

# =========================================================
# PASSWORD HASHING
# =========================================================

def hash_password(password: str) -> str:
    """
    Hash du mot de passe maître (stockage sécurisé)
    """
    return hashlib.sha256(password.encode()).hexdigest()


# =========================================================
# SALT GENERATION
# =========================================================

def generate_salt() -> str:
    """
    Génère un salt aléatoire pour dérivation clé
    """
    return secrets.token_hex(16)


# =========================================================
# KEY DERIVATION
# =========================================================

def derive_master_key(password: str, salt: str) -> str:
    """
    Dérive une clé maître depuis mot de passe + salt
    """
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        150000
    )

    return base64.urlsafe_b64encode(key[:32]).decode()


# =========================================================
# ENCRYPTION
# =========================================================

def encrypt(data: bytes, key: str) -> bytes:
    """
    Chiffre des données avec Fernet
    """
    return Fernet(key.encode()).encrypt(data)


# =========================================================
# DECRYPTION
# =========================================================

def decrypt(data: bytes, key: str) -> bytes:
    """
    Déchiffre des données avec Fernet
    """
    return Fernet(key.encode()).decrypt(data)


# =========================================================
# ENTRY KEY DERIVATION
# =========================================================

def derive_entry_key(master_key: str, entry_id: str) -> str:
    """
    Dérive une clé d'entrée depuis la clé maître + ID
    """
    combined = f"{master_key}:{entry_id}"
    key = hashlib.sha256(combined.encode()).digest()
    return base64.urlsafe_b64encode(key[:32]).decode()


# =========================================================
# DATA INTEGRITY HASH
# =========================================================

def hash_data_with_key(data: str, key: str) -> str:
    """
    Génère un hash SHA256 des données + clé pour vérification d'intégrité
    """
    combined = f"{data}:{key}"
    return hashlib.sha256(combined.encode()).hexdigest()