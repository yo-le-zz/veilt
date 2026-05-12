#!/usr/bin/env python3
"""
🧠 VEIL Memory Dump Attack Test (Simplified)
Test d'attaque réel qui essaie de dump et modifier la mémoire VEIL
"""

import os
import sys
import time
import gc

# Ajouter le dossier parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import VEIL modules
from vault.crypto import *
from vault.ram import *
from vault.daemon import *
from vault.logs import log_attack, log_panic_trigger, log_anti_dump_trigger
from vault.antimem import scan_threats, get_protection_status

class MemoryAttackTest:
    def __init__(self):
        self.test_password = "MemoryAttack@2025!"
        self.sensitive_data = "TOP_SECRET_DATA_2025_MUST_NOT_BE_EXPOSED"
        self.attack_results = []
        
    def log_attack(self, attack_name: str, success: bool, details: str = ""):
        """Log les résultats d'attaque"""
        status = "✅ SUCCESS" if success else "❌ FAILED"
        self.attack_results.append({
            'attack': attack_name,
            'status': status,
            'details': details,
            'success': success
        })
        
        # Log l'attaque dans le système VEIL
        try:
            from vault.logs import log_attack
            log_attack(attack_name, "memory_test", not success, {"details": details})
        except:
            pass
        
        print(f"{status} {attack_name}: {details}")
        
    def setup_sensitive_data(self):
        """Configure des données sensibles dans VEIL"""
        print("🔐 Configuration des données sensibles...")
        try:
            master_key = derive_master_key(self.test_password, "veil_salt")
            encrypted_data = encrypt(self.sensitive_data.encode(), master_key)
            
            # Stocker plusieurs entrées sensibles
            sensitive_entries = [
                ("secret_001", "CLASSIFIED_INTEL_2025"),
                ("secret_002", "TOP_SECRET_DOSSIER"),
                ("secret_003", "CONFIDENTIAL_ACCESS_CODES"),
                ("secret_004", "SENSITIVE_OPERATIONS_DATA"),
                ("secret_005", "CRITICAL_SYSTEM_KEYS")
            ]
            
            for entry_id, data in sensitive_entries:
                encrypted = encrypt(data.encode(), master_key)
                store(entry_id.encode(), encrypted)
                print(f"   📦 Entrée sensible {entry_id} stockée")
            
            return True
        except Exception as e:
            print(f"   ❌ Erreur configuration: {e}")
            return False
    
    def attack_ram_scan(self):
        """Test 1: Scan direct de la RAM VEIL"""
        print("\n🎯 ATTAQUE 1: Scan RAM VEIL")
        try:
            # Essayer de lire directement depuis la RAM VEIL
            test_keys = [
                "secret_001",
                "secret_002", 
                "secret_003",
                "secret_004",
                "secret_005"
            ]
            
            leaked_data = []
            for key in test_keys:
                try:
                    data = get(key)
                    if data and data != b'VEIL::FAKE_DATA_BLOCK':
                        # Essayer de déchiffrer
                        try:
                            master_key = derive_master_key(self.test_password, "veil_salt")
                            decrypted = decrypt(data, master_key).decode()
                            if "SECRET" in decrypted or "TOP_SECRET" in decrypted:
                                leaked_data.append(decrypted)
                        except:
                            pass
                except:
                    pass
            
            if leaked_data:
                self.log_attack("RAM Scan", False, f"Fuite de {len(leaked_data)} données sensibles!")
                for data in leaked_data:
                    print(f"      🔓 FUIT: {data}")
            else:
                self.log_attack("RAM Scan", True, "Aucune fuite détectée (protection OK)")
                
        except Exception as e:
            self.log_attack("RAM Scan", False, f"Erreur scan: {e}")
    
    def attack_memory_injection(self):
        """Test 2: Injection de mémoire malveillante"""
        print("\n🎯 ATTAQUE 2: Injection mémoire malveillante")
        try:
            # Essayer d'écrire des données malveillantes dans la RAM
            malicious_payloads = [
                "HACKED_BY_ATTACKER",
                "MEMORY_COMPROMISED",
                "VEIL_BREACHED"
            ]
            
            injection_success = False
            for payload in malicious_payloads:
                try:
                    # Essayer d'écraser des entrées existantes
                    store("secret_001", payload.encode())
                    
                    # Vérifier si l'injection a réussi
                    check_data = get("secret_001")
                    if check_data and check_data.decode() == payload:
                        injection_success = True
                        self.log_attack("Memory Injection", False, f"Injection réussie: {payload}")
                        break
                except:
                    continue
            
            if not injection_success:
                self.log_attack("Memory Injection", True, "Injection bloquée (protection OK)")
                
        except Exception as e:
            self.log_attack("Memory Injection", False, f"Erreur injection: {e}")
    
    def attack_rapid_access(self):
        """Test 3: Accès rapide pour déclencher le mode panic"""
        print("\n🎯 ATTAQUE 3: Accès rapide (déclenchement panic)")
        try:
            panic_triggered = False
            fake_data_count = 0
            
            # D'abord vérifier si le mode panic est déjà actif
            from vault.ram import is_panic_mode
            initial_panic = is_panic_mode()
            print(f"   📊 Mode panic initial: {initial_panic}")
            
            # Faire des accès très rapides SANS pause pour déclencher l'anti-dump
            print("   ⚡ Début attaque accès rapide...")
            for i in range(50):  # Moins d'itérations mais plus rapides
                try:
                    data = get("secret_001")
                    if data == b'VEIL::FAKE_DATA_BLOCK':
                        fake_data_count += 1
                        fake_data_str = data.decode()
                        print(f"      🚨 FAUX DONNÉES RETOURNÉES #{fake_data_count}: '{fake_data_str}'")
                        print(f"      🛡️ VEIL bloque l'attaque avec des données fictives!")
                        
                        # Log le déclenchement du panic mode
                        try:
                            log_panic_trigger("rapid_access_test")
                        except:
                            pass
                        
                        if fake_data_count > 2:  # Mode panic déclenché
                            panic_triggered = True
                            break
                    else:
                        if i < 5:  # Montrer les premiers accès réussis
                            try:
                                data_preview = data[:50].decode() if len(data) > 50 else data.decode()
                                print(f"      ✅ Accès #{i+1}: données réelles ('{data_preview}...')")
                            except:
                                print(f"      ✅ Accès #{i+1}: données chiffrées ({len(data)} bytes)")
                except Exception as e:
                    print(f"      ❌ Erreur accès #{i+1}: {e}")
                # Pas de pause - accès ultra-rapide
            
            # Vérifier le statut final du mode panic
            final_panic = is_panic_mode()
            print(f"   📊 Mode panic final: {final_panic}")
            
            if panic_triggered or final_panic:
                self.log_attack("Rapid Access", True, f"Mode panic déclenché ({fake_data_count} faux retours)")
            else:
                self.log_attack("Rapid Access", False, f"Mode panic non déclenché ({fake_data_count} faux retours)")
                
        except Exception as e:
            self.log_attack("Rapid Access", False, f"Erreur accès rapide: {e}")
    
    def attack_gc_force(self):
        """Test 4: Forcer le garbage collector pour révéler des données"""
        print("\n🎯 ATTAQUE 4: Force GC + Memory inspection")
        try:
            # Forcer le garbage collector
            for i in range(5):
                gc.collect()
                time.sleep(0.1)
            
            # Inspecter la mémoire après GC
            leaked_after_gc = False
            try:
                # Scanner les objets Python pour trouver des données VEIL
                for obj in gc.get_objects():
                    if hasattr(obj, '__class__') and 'bytes' in str(type(obj)):
                        try:
                            data_str = str(obj)
                            if "SECRET" in data_str or "TOP_SECRET" in data_str:
                                leaked_after_gc = True
                                break
                        except:
                            pass
            except:
                pass
            
            if leaked_after_gc:
                self.log_attack("Force GC", False, "Données sensibles trouvées après GC")
            else:
                self.log_attack("Force GC", True, "GC forcé sans fuite détectée")
                
        except Exception as e:
            self.log_attack("Force GC", False, f"Erreur GC: {e}")
    
    def attack_boundary_testing(self):
        """Test 5: Test des limites et conditions extrêmes"""
        print("\n🎯 ATTAQUE 5: Test des limites")
        try:
            # Test avec des clés invalides
            invalid_keys = [
                "",  # Clé vide
                "\x00" * 100,  # Clé nulle
                "non_existent_key",  # Clé inexistante
                "\xFF" * 50,  # Clé avec octets invalides
            ]
            
            boundary_breached = False
            for invalid_key in invalid_keys:
                try:
                    result = get(invalid_key)
                    if result and result != b'VEIL::FAKE_DATA_BLOCK':
                        boundary_breached = True
                        self.log_attack("Boundary Testing", False, f"Limite franchie avec clé: {invalid_key[:20]}...")
                        break
                except:
                    pass
            
            if not boundary_breached:
                self.log_attack("Boundary Testing", True, "Toutes les limites respectées")
                
        except Exception as e:
            self.log_attack("Boundary Testing", False, f"Erreur test limites: {e}")
    
    def attack_concurrent_access(self):
        """Test 6: Accès concurrents pour trouver des vulnérabilités"""
        print("\n🎯 ATTAQUE 6: Accès concurrents")
        try:
            # Simuler des accès concurrents
            import threading
            
            results = []
            def concurrent_reader():
                try:
                    for i in range(50):
                        data = get("secret_001")
                        if data and data != b'VEIL::FAKE_DATA_BLOCK':
                            results.append(data)
                except:
                    pass
            
            # Lancer plusieurs threads
            threads = []
            for _ in range(5):
                t = threading.Thread(target=concurrent_reader)
                threads.append(t)
                t.start()
            
            # Attendre la fin
            for t in threads:
                t.join()
            
            # Analyser les résultats
            if results:
                self.log_attack("Concurrent Access", False, f"Fuite concurrente: {len(results)} accès réussis")
            else:
                self.log_attack("Concurrent Access", True, "Protection concurrente OK")
                
        except Exception as e:
            self.log_attack("Concurrent Access", False, f"Erreur accès concurrent: {e}")
    
    def attack_pymem_protection(self):
        """Test 7: Test de protection anti-PyMem"""
        print("\n🎯 ATTAQUE 7: Test protection anti-PyMem")
        try:
            # Scanner les menaces PyMem
            print("   🔍 Scan des menaces PyMem...")
            threat_report = scan_threats()
            
            # Vérifier le statut de protection
            protection_status = get_protection_status()
            
            # Analyser les résultats
            threat_level = threat_report.get('threat_level', 'UNKNOWN')
            protection_enabled = protection_status.get('protection_enabled', False)
            
            print(f"   📊 Niveau de menace: {threat_level}")
            print(f"   🛡️ Protection activée: {'OUI' if protection_enabled else 'NON'}")
            
            # Vérifier les imports suspects
            suspicious_imports = threat_report.get('suspicious_imports', [])
            if suspicious_imports:
                print(f"   ⚠️ Imports suspects détectés: {len(suspicious_imports)}")
                for imp in suspicious_imports[:3]:  # Limiter l'affichage
                    print(f"      📦 {imp}")
            else:
                print(f"   ✅ Aucun import suspect détecté")
            
            # Vérifier les debuggers
            debugger_attached = threat_report.get('debugger_attached', False)
            if debugger_attached:
                print(f"   🚨 Debugger attaché: OUI")
                self.log_attack("PyMem Protection", False, "Debugger détecté")
            else:
                print(f"   ✅ Aucun debugger détecté")
            
            # Vérifier les anomalies mémoire
            memory_anomalies = threat_report.get('memory_anomalies', {})
            if any(memory_anomalies.values()):
                print(f"   🔍 Anomalies mémoire détectées")
                for anomaly, detected in memory_anomalies.items():
                    if detected:
                        print(f"      ⚠️ {anomaly}")
                self.log_attack("PyMem Protection", False, "Anomalies mémoire détectées")
            else:
                print(f"   ✅ Aucune anomalie mémoire détectée")
            
            # Évaluer la protection
            if threat_level == 'LOW' and protection_enabled:
                self.log_attack("PyMem Protection", True, f"Protection OK - menace {threat_level}")
            elif threat_level in ['MEDIUM', 'HIGH'] and protection_enabled:
                self.log_attack("PyMem Protection", True, f"Protection active - menace {threat_level} gérée")
            elif threat_level == 'CRITICAL':
                self.log_attack("PyMem Protection", False, f"Menace critique {threat_level} - protection dépassée")
            else:
                self.log_attack("PyMem Protection", False, f"Protection désactivée ou menace {threat_level}")
                
        except Exception as e:
            self.log_attack("PyMem Protection", False, f"Erreur test PyMem: {e}")
    
    def cleanup_test_data(self):
        """Nettoie les données de test"""
        try:
            test_entries = ["secret_001", "secret_002", "secret_003", "secret_004", "secret_005"]
            for entry in test_entries:
                try:
                    erase_entry(entry)
                except:
                    pass
        except:
            pass
    
    def run_all_attacks(self):
        """Exécute tous les tests d'attaque"""
        print("🚨 VEIL MEMORY ATTACK TEST SUITE")
        print("=" * 50)
        print("⚠️  CE TEST SIMULE DES ATTAQUES RÉELLES CONTRE VEIL")
        print("⚠️  VÉRIFICATION DES PROTECTIONS ANTI-DUMP ET ANTI-FORENSIC")
        print("=" * 50)
        
        # Configuration des données sensibles
        if not self.setup_sensitive_data():
            print("❌ Impossible de configurer les données de test")
            return False
        
        # Exécuter toutes les attaques
        attacks = [
            self.attack_ram_scan,
            self.attack_memory_injection,
            self.attack_rapid_access,
            self.attack_gc_force,
            self.attack_boundary_testing,
            self.attack_concurrent_access,
            self.attack_pymem_protection
        ]
        
        for attack in attacks:
            try:
                attack()
            except Exception as e:
                print(f"   💥 Erreur critique dans {attack.__name__}: {e}")
        
        # Nettoyer
        self.cleanup_test_data()
        
        # Résultats
        print("\n" + "=" * 50)
        print("📊 ATTACK RESULTS SUMMARY")
        print("=" * 50)
        
        successful_attacks = sum(1 for r in self.attack_results if r['success'])
        failed_attacks = len(self.attack_results) - successful_attacks
        
        print(f"✅ Successful defenses: {successful_attacks}")
        print(f"❌ Failed defenses: {failed_attacks}")
        print(f"📈 Security score: {(successful_attacks/len(self.attack_results)*100):.1f}%")
        
        print("\n📋 Detailed Results:")
        for result in self.attack_results:
            print(f"  {result['status']} {result['attack']}: {result['details']}")
        
        if failed_attacks == 0:
            print(f"\n🎉 EXCELLENT! VEIL a résisté à toutes les attaques!")
            print("🛡️ Système sécurisé contre les dumps mémoire")
            return True
        else:
            print(f"\n⚠️ {failed_attacks} vulnérabilités détectées!")
            print("🔧 Améliorez les protections anti-dump")
            return False

def main():
    """Point d'entrée principal"""
    print("🧠 Starting VEIL Memory Attack Test...")
    
    attacker = MemoryAttackTest()
    success = attacker.run_all_attacks()
    
    if success:
        print("\n✅ Memory attack test completed successfully!")
        print("🛡️ VEIL memory protections are working correctly")
        sys.exit(0)
    else:
        print("\n❌ Memory attack test revealed vulnerabilities!")
        print("🚨 Review and strengthen memory protections")
        sys.exit(1)

if __name__ == "__main__":
    main()
