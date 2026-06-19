import hashlib
import secrets

# =========================================================
# ID GENERATION
# =========================================================

def generate_id(data: str) -> str:
    """
    Génère un ID unique basé sur données + random
    """
    raw = data + secrets.token_hex(8)
    return hashlib.sha256(raw.encode()).hexdigest()[:12]