"""
veil.antimem
=============
Lightweight, best-effort detection of memory-inspection tooling running
in the same process (PyMem-style libraries, debuggers attached via
common env-var conventions, abnormal object-graph growth).

This is NOT a substitute for OS-level process protection - it is one
extra signal Vault uses to decide whether to escalate into panic mode.
Refactored from the original module-level singleton into a plain class
with no shared global state, so multiple Vault instances (or running
the test suite) don't interfere with each other.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Dict, List

SUSPICIOUS_MODULES = [
    "pymem", "pymem.ressources", "pymem.process", "pymem.memory",
    "pymem.exception", "pymem.thread",
    "readprocessmemory", "writeprocessmemory", "memoryhack", "memedit",
    "cheatengine", "ollydbg", "x64dbg", "windbg",
]


class ThreatScanner:
    def __init__(self) -> None:
        self.enabled = True
        self.history: List[Dict] = []

    def check_suspicious_imports(self) -> List[str]:
        found = []
        try:
            for module_name in list(sys.modules.keys()):
                lowered = module_name.lower()
                if any(sus in lowered for sus in SUSPICIOUS_MODULES):
                    found.append(module_name)
        except Exception:
            pass
        return found

    def check_debugger_attached(self) -> bool:
        try:
            if any(os.environ.get(var) for var in ("PYTHONDEBUG", "PDB", "VEIL_DEBUG")):
                return True
            if sys.gettrace() is not None:
                return True
        except Exception:
            pass
        return False

    def check_memory_anomalies(self) -> Dict[str, bool]:
        anomalies = {"unusual_allocations": False, "memory_scanning": False}
        try:
            import gc
            objects = gc.get_objects()
            if len(objects) > 200_000:
                anomalies["memory_scanning"] = True
            large = [o for o in objects if hasattr(o, "__sizeof__") and o.__sizeof__() > 1024 * 1024]
            if len(large) > 10:
                anomalies["unusual_allocations"] = True
        except Exception:
            pass
        return anomalies

    def scan(self) -> Dict:
        if not self.enabled:
            return {"status": "disabled", "threat_level": "LOW"}

        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "suspicious_imports": self.check_suspicious_imports(),
            "debugger_attached": self.check_debugger_attached(),
            "memory_anomalies": self.check_memory_anomalies(),
            "threat_level": "LOW",
        }

        score = 0
        score += len(report["suspicious_imports"]) * 3
        score += 5 if report["debugger_attached"] else 0
        score += 3 if any(report["memory_anomalies"].values()) else 0

        if score >= 10:
            report["threat_level"] = "CRITICAL"
        elif score >= 5:
            report["threat_level"] = "HIGH"
        elif score >= 2:
            report["threat_level"] = "MEDIUM"

        self.history.append(report)
        return report

    def status(self) -> Dict:
        return {
            "enabled": self.enabled,
            "total_scans": len(self.history),
            "last_scan": self.history[-1] if self.history else None,
        }
