import threading
import time
import tempfile
import os
import json
from datetime import datetime
from enum import Enum

# =========================================================
# ENTRY STATUS
# =========================================================

class EntryStatus(Enum):
    ACTIVE = "ACTIVE"
    DELETED = "DELETED"
    CRASHED = "CRASHED"
    CORRUPTED = "CORRUPTED"

# =========================================================
# DAEMON STATE
# =========================================================

RUNNING = False
INDEX = {}
DAEMON_LOCK = threading.Lock()

TEMP_DIR = os.path.join(tempfile.gettempdir(), "veil_vault")


# =========================================================
# INTERNAL UTILITIES
# =========================================================

def _ensure_temp_dir():
    os.makedirs(TEMP_DIR, exist_ok=True)


def _save_data(entry_id: str, encrypted_data: bytes):
    """
    Sauvegarde les données chiffrées sur disque
    """
    data_file = os.path.join(TEMP_DIR, f"{entry_id}.data")
    with open(data_file, "wb") as f:
        f.write(encrypted_data)


def _load_data(entry_id: str) -> bytes:
    """
    Charge les données chiffrées depuis le disque
    """
    data_file = os.path.join(TEMP_DIR, f"{entry_id}.data")
    if os.path.exists(data_file):
        with open(data_file, "rb") as f:
            return f.read()
    return None


def _sync_index():
    """
    Synchronise l'INDEX sur disque
    """
    with open(os.path.join(TEMP_DIR, "index.json"), "w") as f:
        json.dump(INDEX, f, indent=2)


def _load_index():
    """
    Charge l'index depuis fichier temporaire
    """
    global INDEX
    index_file = os.path.join(TEMP_DIR, "index.json")
    if os.path.exists(index_file):
        try:
            with open(index_file, "r") as f:
                INDEX = json.load(f)
        except:
            INDEX = {}


def _detect_crashes():
    """
    Détecte les entrées qui ont crashé (présentes dans INDEX mais pas en RAM)
    """
    from . import ram
    
    crashed_entries = []
    for entry_id, metadata in INDEX.items():
        if metadata.get("status") == EntryStatus.ACTIVE.value:
            # Vérifier si l'entrée était précédemment en RAM
            # Si elle vient d'être créée (même timestamp), ne pas la considérer comme crashée
            created_at = metadata.get("created_at", "")
            last_seen = metadata.get("last_seen", "")
            
            # Si les timestamps sont très proches (< 5 secondes), c'est une nouvelle entrée
            try:
                from datetime import datetime as dt
                created_dt = dt.fromisoformat(created_at)
                seen_dt = dt.fromisoformat(last_seen)
                time_diff = abs((seen_dt - created_dt).total_seconds())
                
                if time_diff < 5:
                    # Entrée récente, ignorer la détection de crash
                    continue
            except:
                pass
            
            # Pour les entrées plus anciennes, vérifier si elles sont en RAM
            ram_result = ram.get(entry_id)
            if not ram_result or ram_result == b'VEIL::FAKE_DATA_BLOCK':
                metadata["status"] = EntryStatus.CRASHED.value
                metadata["last_seen"] = datetime.now().isoformat()
                crashed_entries.append(entry_id)
    
    return crashed_entries


# =========================================================
# DAEMON START
# =========================================================

def start_daemon():
    """
    Lance le daemon mémoire
    """
    global RUNNING, INDEX
    if RUNNING:
        return  # Déjà démarré
    
    RUNNING = True
    _ensure_temp_dir()
    _load_index()  # Charger depuis fichier
    _detect_crashes()
    
    print(f"DEBUG: Daemon démarré, INDEX chargé: {len(INDEX)} entrées")

    def loop():
        global RUNNING
        while RUNNING:
            time.sleep(2)
            _detect_crashes()
            _sync_index()

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    
    # Attendre un peu pour l'initialisation
    time.sleep(0.1)


# =========================================================
# DAEMON STOP (CLEAN WIPE)
# =========================================================

def stop_daemon():
    """
    Stop + wipe mémoire + fichiers temp
    """
    global RUNNING
    RUNNING = False

    INDEX.clear()

    if os.path.exists(TEMP_DIR):
        for f in os.listdir(TEMP_DIR):
            try:
                os.remove(os.path.join(TEMP_DIR, f))
            except:
                pass


# =========================================================
# INDEX MANAGEMENT
# =========================================================

def register_entry(entry_id: str, data_hash: str = None, encrypted_data: bytes = None):
    """
    Enregistre une nouvelle entrée dans l'INDEX avec persistance des données
    """
    with DAEMON_LOCK:
        INDEX[entry_id] = {
            "status": EntryStatus.ACTIVE.value,
            "created_at": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "data_hash": data_hash,
            "access_count": 0
        }
        
        # Persister les données chiffrées sur disque
        if encrypted_data:
            _save_data(entry_id, encrypted_data)
        
        # Synchroniser immédiatement pour persistance
        _sync_index()
        print(f"DEBUG: Entry {entry_id} registered and synced with data")


def update_entry_status(entry_id: str, status: EntryStatus, reason: str = None):
    """
    Met à jour le statut d'une entrée
    """
    with DAEMON_LOCK:
        if entry_id in INDEX:
            INDEX[entry_id]["status"] = status.value
            INDEX[entry_id]["last_seen"] = datetime.now().isoformat()
            if reason:
                INDEX[entry_id]["reason"] = reason
            # Synchroniser immédiatement pour persistance
            _sync_index()
            print(f"DEBUG: Entry {entry_id} status updated to {status.value}")


def get_entry_status(entry_id: str) -> dict:
    """
    Récupère les infos d'une entrée
    """
    with DAEMON_LOCK:
        return INDEX.get(entry_id, {})


def get_all_entries() -> dict:
    """
    Récupère toutes les entrées
    """
    with DAEMON_LOCK:
        # Si l'INDEX est vide, essayer de charger depuis fichier
        if not INDEX:
            _load_index()
        return INDEX.copy()


def increment_access(entry_id: str):
    """
    Incrémente le compteur d'accès
    """
    with DAEMON_LOCK:
        if entry_id in INDEX:
            INDEX[entry_id]["access_count"] += 1
            INDEX[entry_id]["last_seen"] = datetime.now().isoformat()