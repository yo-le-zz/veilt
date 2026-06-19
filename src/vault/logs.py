import json
import os
import tempfile
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional

# =========================================================
# LOG EVENT TYPES
# =========================================================

class EventType(Enum):
    ENTRY_CREATED = "ENTRY_CREATED"
    ENTRY_ACCESSED = "ENTRY_ACCESSED"
    ENTRY_DELETED = "ENTRY_DELETED"
    ENTRY_CRASHED = "ENTRY_CRASHED"
    AUTH_FAILED = "AUTH_FAILED"
    INTEGRITY_MISMATCH = "INTEGRITY_MISMATCH"
    PANIC_TRIGGERED = "PANIC_TRIGGERED"
    ANTI_DUMP_TRIGGERED = "ANTI_DUMP_TRIGGERED"
    MANUAL_DELETE = "MANUAL_DELETE"

class DeleteReason(Enum):
    USER_REQUEST = "USER_REQUEST"
    AUTH_FAILURE = "AUTH_FAILURE"
    INTEGRITY_MISMATCH = "INTEGRITY_MISMATCH"
    PANIC_WIPE = "PANIC_WIPE"
    ANTI_DUMP = "ANTI_DUMP"
    CRASH_RECOVERY = "CRASH_RECOVERY"

# =========================================================
# LOG SYSTEM STATE
# =========================================================

TEMP_DIR = os.path.join(tempfile.gettempdir(), "veil_vault")
LOG_FILE = os.path.join(TEMP_DIR, "events.log")
ATTACK_LOG_FILE = os.path.join(TEMP_DIR, "attacks.log")

# =========================================================
# INTERNAL UTILITIES
# =========================================================

def _ensure_log_dir():
    """Assure que le répertoire de logs existe"""
    os.makedirs(TEMP_DIR, exist_ok=True)

def _write_log_entry(entry: Dict):
    """Écrit une entrée de log dans le fichier"""
    _ensure_log_dir()
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

# =========================================================
# LOG FUNCTIONS
# =========================================================

def log_event(event_type: EventType, entry_id: str = None, reason: str = None, details: Dict = None):
    """
    Enregistre un événement dans le log
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type.value,
        "entry_id": entry_id,
        "reason": reason,
        "details": details or {}
    }
    
    _write_log_entry(log_entry)

def log_entry_created(entry_id: str, data_hash: str):
    """Log création d'entrée"""
    log_event(
        EventType.ENTRY_CREATED,
        entry_id=entry_id,
        details={"data_hash": data_hash}
    )

def log_entry_accessed(entry_id: str, success: bool = True):
    """Log accès à une entrée"""
    log_event(
        EventType.ENTRY_ACCESSED,
        entry_id=entry_id,
        details={"success": success}
    )

def log_entry_deleted(entry_id: str, reason: DeleteReason):
    """Log suppression d'entrée"""
    log_event(
        EventType.ENTRY_DELETED,
        entry_id=entry_id,
        reason=reason.value
    )

def log_auth_failed(entry_id: str = None):
    """Log échec d'authentification"""
    log_event(
        EventType.AUTH_FAILED,
        entry_id=entry_id
    )

def log_integrity_mismatch(entry_id: str, expected_hash: str, actual_hash: str):
    """Log corruption de données"""
    log_event(
        EventType.INTEGRITY_MISMATCH,
        entry_id=entry_id,
        details={
            "expected_hash": expected_hash,
            "actual_hash": actual_hash
        }
    )

def log_panic_triggered(reason: str):
    """Log déclenchement mode panique"""
    log_event(
        EventType.PANIC_TRIGGERED,
        reason=reason
    )

def log_anti_dump_triggered():
    """Log déclenchement anti-dump"""
    log_event(
        EventType.ANTI_DUMP_TRIGGERED
    )

def log_entry_crashed(entry_id: str):
    """Log détection de crash"""
    log_event(
        EventType.ENTRY_CRASHED,
        entry_id=entry_id
    )

# =========================================================
# LOG RETRIEVAL
# =========================================================

def get_entry_logs(entry_id: str, limit: int = 50) -> List[Dict]:
    """
    Récupère tous les logs pour une entrée spécifique
    """
    if not os.path.exists(LOG_FILE):
        return []
    
    logs = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                log_entry = json.loads(line.strip())
                if log_entry.get("entry_id") == entry_id:
                    logs.append(log_entry)
                    if len(logs) >= limit:
                        break
            except json.JSONDecodeError:
                continue
    
    return logs

def get_all_logs(limit: int = 100) -> List[Dict]:
    """
    Récupère tous les logs récents
    """
    if not os.path.exists(LOG_FILE):
        return []
    
    logs = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
        # Lire les lignes les plus récentes en premier
        for line in reversed(lines[-limit:]):
            try:
                log_entry = json.loads(line.strip())
                logs.append(log_entry)
            except json.JSONDecodeError:
                continue
    
    return logs

def get_logs_by_event_type(event_type: EventType, limit: int = 50) -> List[Dict]:
    """
    Récupère les logs par type d'événement
    """
    if not os.path.exists(LOG_FILE):
        return []
    
    logs = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                log_entry = json.loads(line.strip())
                if log_entry.get("event_type") == event_type.value:
                    logs.append(log_entry)
                    if len(logs) >= limit:
                        break
            except json.JSONDecodeError:
                continue
    
    return logs

def clear_logs():
    """
    Supprime tous les logs
    """
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

# =========================================================
# LOG ANALYSIS
# =========================================================

def get_delete_reason(entry_id: str) -> Optional[str]:
    """
    Récupère la raison de suppression d'une entrée
    """
    logs = get_entry_logs(entry_id)
    for log in logs:
        if log.get("event_type") == EventType.ENTRY_DELETED.value:
            return log.get("reason")
    return None

def get_crash_summary() -> Dict:
    """
    Génère un résumé des crashes détectés
    """
    crash_logs = get_logs_by_event_type(EventType.ENTRY_CRASHED)
    return {
        "total_crashes": len(crash_logs),
        "crashed_entries": [log.get("entry_id") for log in crash_logs],
        "recent_crashes": crash_logs[:10]
    }

# =========================================================
# ATTACK LOGGING
# =========================================================

def log_attack(attack_type: str, source: str = "unknown", blocked: bool = True, details: Dict = None):
    """
    Enregistre une tentative d'attaque
    """
    attack_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": attack_type,
        "source": source,
        "blocked": blocked,
        "details": details or {}
    }
    
    _ensure_log_dir()
    
    with open(ATTACK_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(attack_entry, ensure_ascii=False) + "\n")

def get_attack_logs(limit: int = 50) -> List[Dict]:
    """
    Récupère les logs d'attaques
    """
    if not os.path.exists(ATTACK_LOG_FILE):
        return []
    
    logs = []
    with open(ATTACK_LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                log_entry = json.loads(line.strip())
                logs.append(log_entry)
                if len(logs) >= limit:
                    break
            except json.JSONDecodeError:
                continue
    
    return logs[-limit:]  # Return most recent logs

def log_panic_trigger(source: str = "rapid_access"):
    """
    Enregistre le déclenchement du mode panic
    """
    log_attack("PANIC_TRIGGERED", source, blocked=True, details={
        "fake_data_returned": "VEIL::FAKE_DATA_BLOCK"
    })
    
    # Also log as regular event
    log_event(EventType.PANIC_TRIGGERED, details={"source": source})

def log_anti_dump_trigger(source: str = "memory_scan"):
    """
    Enregistre le déclenchement de l'anti-dump
    """
    log_attack("ANTI_DUMP_TRIGGERED", source, blocked=True, details={
        "protection": "fake_data_injection"
    })
    
    # Also log as regular event
    log_event(EventType.ANTI_DUMP_TRIGGERED, details={"source": source})