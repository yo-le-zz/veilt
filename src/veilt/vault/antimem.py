#!/usr/bin/env python3
"""
🛡️ VEIL Anti-Memory Hacking Protection (Simplified)
Protection contre PyMem et autres outils de hacking mémoire
"""

import os
import sys
import time
from typing import List, Dict, Optional
from datetime import datetime

# Known memory hacking libraries
SUSPICIOUS_MODULES = [
    'pymem', 'pymem.ressources', 'pymem.ressources.structure', 'pymem.ressources.enum',
    'pymem.ressources.exception', 'pymem.ressources.hook', 'pymem.thread',
    'pymem.process', 'pymem.memory', 'pymem.exception', 'pymem.ressources.client',
    'readprocessmemory', 'writeprocessmemory', 'memoryhack', 'memedit',
    'cheatengine', 'ollydbg', 'x64dbg', 'ida', 'windbg', 'gdb'
]

class AntiMemProtection:
    def __init__(self):
        self.detection_enabled = True
        self.panic_triggered = False
        self.detection_log = []
        
    def check_suspicious_imports(self) -> List[str]:
        """Vérifie les imports suspects dans le processus actuel"""
        suspicious_imports = []
        
        try:
            # Vérifier les modules importés
            for module_name in sys.modules.keys():
                if any(sus in module_name.lower() for sus in SUSPICIOUS_MODULES):
                    suspicious_imports.append(module_name)
                    
        except Exception as e:
            suspicious_imports.append(f"Error checking imports: {e}")
            
        return suspicious_imports
    
    def check_debugger_attached(self) -> bool:
        """Vérifie si un debugger est attaché (simplifié)"""
        try:
            # Vérifier les variables d'environnement de debug
            debug_env_vars = ['PYTHONDEBUG', 'PDB', 'DEBUG']
            for var in debug_env_vars:
                if os.environ.get(var):
                    return True
                    
            # Vérifier si nous sommes dans un environnement de test
            if 'test' in sys.argv[0].lower() or 'tests' in sys.argv[0].lower():
                return True
                
        except:
            pass
            
        return False
    
    def check_memory_anomalies(self) -> Dict:
        """Détecte les anomalies de mémoire (simplifié)"""
        anomalies = {
            'unusual_allocations': False,
            'memory_scanning': False,
            'suspicious_patterns': False
        }
        
        try:
            # Vérifier la taille des objets Python
            import gc
            objects = gc.get_objects()
            
            # Si trop d'objets, suspect
            if len(objects) > 100000:
                anomalies['memory_scanning'] = True
                
            # Vérifier les gros objets
            large_objects = [obj for obj in objects if hasattr(obj, '__sizeof__') and obj.__sizeof__() > 1024*1024]
            if len(large_objects) > 10:
                anomalies['unusual_allocations'] = True
                
        except:
            pass
            
        return anomalies
    
    def trigger_panic_mode(self, reason: str):
        """Déclenche le mode panic"""
        if not self.panic_triggered:
            self.panic_triggered = True
            
            # Log l'événement
            try:
                from vault.logs import log_attack
                log_attack("ANTI_MEM_PANIC", "pymem_detection", True, {"reason": reason})
            except:
                pass
            
            # Nettoyer la mémoire sensible
            try:
                from vault.ram import clear_all
                clear_all()
            except:
                pass
    
    def scan_for_threats(self) -> Dict:
        """Scan complet des menaces PyMem"""
        if not self.detection_enabled:
            return {"status": "disabled"}
            
        threat_report = {
            'timestamp': datetime.now().isoformat(),
            'suspicious_imports': [],
            'debugger_attached': False,
            'memory_anomalies': {},
            'suspicious_access': [],
            'threat_level': 'LOW',
            'panic_triggered': False
        }
        
        # 1. Vérifier les imports suspects
        threat_report['suspicious_imports'] = self.check_suspicious_imports()
        
        # 2. Vérifier les debuggers
        threat_report['debugger_attached'] = self.check_debugger_attached()
        
        # 3. Vérifier les anomalies mémoire
        threat_report['memory_anomalies'] = self.check_memory_anomalies()
        
        # 4. Vérifier les accès processus (simplifié)
        threat_report['suspicious_access'] = []
        
        # Calculer le niveau de menace
        threat_score = 0
        if threat_report['suspicious_imports']:
            threat_score += len(threat_report['suspicious_imports']) * 2
        if threat_report['debugger_attached']:
            threat_score += 5
        if any(threat_report['memory_anomalies'].values()):
            threat_score += 3
        if threat_report['suspicious_access']:
            threat_score += len(threat_report['suspicious_access'])
        
        # Déterminer le niveau de menace
        if threat_score >= 10:
            threat_report['threat_level'] = 'CRITICAL'
            self.trigger_panic_mode("Critical threat detected")
            threat_report['panic_triggered'] = True
        elif threat_score >= 5:
            threat_report['threat_level'] = 'HIGH'
        elif threat_score >= 2:
            threat_report['threat_level'] = 'MEDIUM'
        else:
            threat_report['threat_level'] = 'LOW'
        
        # Ajouter au log
        self.detection_log.append(threat_report)
        
        return threat_report
    
    def get_protection_status(self) -> Dict:
        """Retourne le statut de protection"""
        return {
            'protection_enabled': self.detection_enabled,
            'panic_mode': self.panic_triggered,
            'last_scan': self.detection_log[-1] if self.detection_log else None,
            'total_detections': len(self.detection_log)
        }

# Instance globale de protection
anti_mem = AntiMemProtection()

def enable_protection():
    """Active la protection anti-mémoire"""
    anti_mem.detection_enabled = True

def disable_protection():
    """Désactive la protection anti-mémoire"""
    anti_mem.detection_enabled = False

def scan_threats():
    """Effectue un scan des menaces"""
    return anti_mem.scan_for_threats()

def get_protection_status():
    """Retourne le statut de protection"""
    return anti_mem.get_protection_status()

def is_panic_triggered():
    """Vérifie si le mode panic est déclenché"""
    return anti_mem.panic_triggered

# Protection automatique au démarrage
def auto_protect():
    """Protection automatique au démarrage de VEIL"""
    try:
        # Scanner immédiatement les menaces
        threat_report = scan_threats()
        
        if threat_report.get('threat_level') in ['HIGH', 'CRITICAL']:
            try:
                from vault.logs import log_attack
                log_attack("AUTO_PROTECTION_TRIGGERED", "startup_scan", True, threat_report)
            except:
                pass
            
        return threat_report
    except:
        return {"status": "protection_failed"}
