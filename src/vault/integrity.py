import hashlib
import hmac
from typing import Optional, Tuple
from .crypto import hash_data_with_key

# =========================================================
# HASHING CORE
# =========================================================

def hash_data(data: bytes) -> str:
    """
    Hash brut des données (intégrité)
    """
    return hashlib.sha256(data).hexdigest()

def hash_data_secure(data: bytes, key: bytes) -> str:
    """
    Hash sécurisé avec HMAC pour protection anti-tampering
    """
    return hmac.new(key, data, hashlib.sha256).hexdigest()

# =========================================================
# VERIFICATION
# =========================================================

def verify_hash(data: bytes, expected_hash: str) -> bool:
    """
    Vérifie que les données n'ont pas été modifiées
    """
    return hash_data(data) == expected_hash

def verify_hash_secure(data: bytes, expected_hash: str, key: bytes) -> bool:
    """
    Vérification sécurisée avec HMAC
    """
    return hmac.compare_digest(hash_data_secure(data, key), expected_hash)

def verify_entry_integrity(data: bytes, expected_hash: str, entry_key: str) -> Tuple[bool, Optional[str]]:
    """
    Vérification complète d'intégrité d'une entrée
    
    Returns:
        (is_valid, actual_hash)
    """
    try:
        # Hash avec la clé d'entrée pour vérification
        combined = f"{data.decode('utf-8', errors='ignore')}:{entry_key}"
        actual_hash = hashlib.sha256(combined.encode()).hexdigest()
        
        is_valid = hmac.compare_digest(actual_hash, expected_hash)
        return is_valid, actual_hash
        
    except Exception as e:
        return False, f"ERROR: {str(e)}"

def detect_corruption(data: bytes, expected_hash: str, entry_key: str) -> dict:
    """
    Analyse détaillée de corruption potentielle
    """
    result = {
        "is_corrupted": False,
        "corruption_type": None,
        "details": {}
    }
    
    try:
        # Vérification basique
        basic_hash = hash_data(data)
        if basic_hash != expected_hash:
            result["is_corrupted"] = True
            result["corruption_type"] = "BASIC_HASH_MISMATCH"
            result["details"]["basic_expected"] = expected_hash
            result["details"]["basic_actual"] = basic_hash
        
        # Vérification avec clé
        is_valid, actual_hash = verify_entry_integrity(data, expected_hash, entry_key)
        if not is_valid and not result["is_corrupted"]:
            result["is_corrupted"] = True
            result["corruption_type"] = "KEYED_HASH_MISMATCH"
            result["details"]["keyed_expected"] = expected_hash
            result["details"]["keyed_actual"] = actual_hash
        
        # Vérification de structure
        try:
            decoded = data.decode('utf-8')
            if len(decoded) < 10:  # Seuil minimal
                result["is_corrupted"] = True
                result["corruption_type"] = "DATA_TOO_SHORT"
                result["details"]["length"] = len(decoded)
        except UnicodeDecodeError:
            result["is_corrupted"] = True
            result["corruption_type"] = "ENCODING_CORRUPTION"
            
    except Exception as e:
        result["is_corrupted"] = True
        result["corruption_type"] = "VERIFICATION_ERROR"
        result["details"]["error"] = str(e)
    
    return result

def generate_integrity_report(data: bytes, entry_key: str) -> dict:
    """
    Génère un rapport d'intégrité complet pour des données
    """
    try:
        basic_hash = hash_data(data)
        keyed_hash = hash_data_with_key(data.decode('utf-8', errors='ignore'), entry_key)
        
        return {
            "status": "VALID",
            "basic_hash": basic_hash,
            "keyed_hash": keyed_hash,
            "data_size": len(data),
            "encoding": "utf-8",
            "verification_timestamp": hashlib.sha256(str(hash(data)).encode()).hexdigest()[:16]
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "error": str(e),
            "data_size": len(data) if data else 0
        }