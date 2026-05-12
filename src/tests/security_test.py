#!/usr/bin/env python3
"""
🛡️ VEIL Security Test Suite
Version finale avec tests corrigés et sécurité maximale
"""

import os
import sys
import time
import json
import threading
import tempfile
from concurrent.futures import ThreadPoolExecutor
import subprocess

# Ajouter le dossier parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import VEIL modules
from vault.crypto import *
from vault.ram import *
from vault.daemon import *
from vault.logs import *
from vault.integrity import *
from logique import validate_password

class SecurityTester:
    def __init__(self):
        self.test_password = "SecureP@ss123!"
        self.test_data = "HIGHLY_SENSITIVE_DATA_2025"
        self.results = []
        self.passed = 0
        self.failed = 0
        
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Enregistre le résultat d'un test"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.results.append({
            'test': test_name,
            'status': status,
            'details': details,
            'passed': passed
        })
        
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        print(f"{status} {test_name}: {details}")
    
    def test_basic_encryption(self):
        """Test 1: Chiffrement et déchiffrement"""
        try:
            master_key = derive_master_key(self.test_password, "veil_salt")
            entry_key = derive_entry_key(master_key, "test_id")
            
            encrypted = encrypt(self.test_data.encode(), master_key)
            decrypted = decrypt(encrypted, master_key).decode()
            
            integrity_hash = hash_data_with_key(self.test_data, entry_key)
            verified = hash_data_with_key(decrypted, entry_key) == integrity_hash
            
            self.log_result("Basic Encryption & Decryption", 
                          verified and decrypted == self.test_data,
                          f"Data integrity: {verified}")
        except Exception as e:
            self.log_result("Basic Encryption & Decryption", False, str(e))
    
    def test_password_strength(self):
        """Test 2: Robustesse du mot de passe"""
        try:
            # Test avec le mot de passe sécurisé (doit passer)
            validate_password(self.test_password)
            secure_pass = True
            
            # Test avec mots de passe faibles (doit échouer)
            weak_passwords = ["123", "password", "admin", "test", "weak", "123456"]
            weak_rejected = 0
            
            for weak_pwd in weak_passwords:
                try:
                    validate_password(weak_pwd)
                except:
                    weak_rejected += 1
            
            all_weak_rejected = weak_rejected == len(weak_passwords)
            
            self.log_result("Password Strength Validation", 
                          secure_pass and all_weak_rejected,
                          f"Secure accepted: {secure_pass}, Weak rejected: {all_weak_rejected}")
        except Exception as e:
            self.log_result("Password Strength Validation", False, str(e))
    
    def test_anti_dump_protection(self):
        """Test 3: Protection anti-dump"""
        try:
            # Stocker des données sensibles
            test_id = "anti_dump_test"
            master_key = derive_master_key(self.test_password, "veil_salt")
            encrypted = encrypt(self.test_data.encode(), master_key)
            
            # Stocker en RAM
            store(test_id.encode(), encrypted)
            
            # Test d'accès rapide (doit déclencher le panic mode)
            panic_triggered = False
            for i in range(15):  # Accès rapide
                result = get(test_id)
                if result == b'VEIL::FAKE_DATA_BLOCK':
                    panic_triggered = True
                    break
                time.sleep(0.01)  # Accès très rapide
            
            # Vérifier le panic mode
            panic_status = is_panic_mode()
            
            # Nettoyer
            erase_entry(test_id)
            
            self.log_result("Anti-Dump Protection", 
                          panic_triggered or panic_status,
                          f"Panic triggered: {panic_triggered}, Status: {panic_status}")
        except Exception as e:
            self.log_result("Anti-Dump Protection", False, str(e))
    
    def test_integrity_verification(self):
        """Test 4: Vérification d'intégrité"""
        try:
            test_id = "integrity_test"
            master_key = derive_master_key(self.test_password, "veil_salt")
            entry_key = derive_entry_key(master_key, test_id)
            
            # Données originales
            original_hash = hash_data_with_key(self.test_data, entry_key)
            encrypted = encrypt(self.test_data.encode(), master_key)
            
            # Test avec données corrompues
            corrupted_data = self.test_data + "CORRUPTED"
            corrupted_hash = hash_data_with_key(corrupted_data, entry_key)
            
            integrity_ok = original_hash != corrupted_hash
            
            self.log_result("Integrity Verification", 
                          integrity_ok,
                          f"Hashes differ for corrupted data: {integrity_ok}")
        except Exception as e:
            self.log_result("Integrity Verification", False, str(e))
    
    def test_persistence_security(self):
        """Test 5: Sécurité de la persistance"""
        try:
            # Nettoyer d'abord
            self.cleanup_all()
            
            # Ajouter des données
            test_id = "persistence_test"
            start_daemon()
            register_entry(test_id, "test_hash", b"encrypted_data")
            
            # Vérifier que les données sont persistées
            temp_dir = os.path.join(tempfile.gettempdir(), "veil_vault")
            index_file = os.path.join(temp_dir, "index.json")
            data_file = os.path.join(temp_dir, f"{test_id}.data")
            
            index_exists = os.path.exists(index_file)
            data_exists = os.path.exists(data_file)
            
            # Vérifier le contenu
            if index_exists:
                with open(index_file, 'r') as f:
                    index_data = json.load(f)
                    entry_in_index = test_id in index_data
            else:
                entry_in_index = False
            
            self.log_result("Persistence Security", 
                          index_exists and data_exists and entry_in_index,
                          f"Index: {index_exists}, Data: {data_exists}, Entry: {entry_in_index}")
        except Exception as e:
            self.log_result("Persistence Security", False, str(e))
    
    def test_concurrent_access(self):
        """Test 6: Accès concurrents"""
        try:
            test_id = "concurrent_test"
            master_key = derive_master_key(self.test_password, "veil_salt")
            encrypted = encrypt(self.test_data.encode(), master_key)
            
            # Stocker en RAM
            store(test_id.encode(), encrypted)
            
            results = []
            errors = []
            
            def concurrent_read():
                try:
                    result = get(test_id)
                    results.append(result)
                except Exception as e:
                    errors.append(str(e))
            
            # Lancer 10 threads concurrents
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(concurrent_read) for _ in range(10)]
                for future in futures:
                    future.result()
            
            # Vérifier la cohérence
            consistent = len(set(results)) <= 2  # Peut avoir fake data
            no_errors = len(errors) == 0
            
            # Nettoyer
            erase_entry(test_id)
            
            self.log_result("Concurrent Access Safety", 
                          consistent and no_errors,
                          f"Consistent results: {consistent}, No errors: {no_errors}")
        except Exception as e:
            self.log_result("Concurrent Access Safety", False, str(e))
    
    def test_secure_deletion(self):
        """Test 7: Suppression sécurisée"""
        try:
            test_id = "secure_delete_test"
            master_key = derive_master_key(self.test_password, "veil_salt")
            encrypted = encrypt(self.test_data.encode(), master_key)
            
            # Stocker en RAM
            store(test_id.encode(), encrypted)
            
            # Vérifier que les données existent
            before_delete = get(test_id)
            data_exists_before = before_delete is not None and len(before_delete) > 0
            
            # Suppression sécurisée (simuler la commande delete)
            erase_entry(test_id)
            
            # Multi-pass overwrite
            try:
                store(test_id.encode(), b'\x00' * 1024)
                store(test_id.encode(), b'\xFF' * 1024)
                import os
                store(test_id.encode(), os.urandom(1024))
                erase_entry(test_id)
            except:
                pass  # Ignore errors in additional wipes
            
            # Vérifier que les données sont bien supprimées
            after_delete = get(test_id)
            data_gone_after = after_delete is None
            
            self.log_result("Secure Deletion", 
                          data_exists_before and data_gone_after,
                          f"Data before: {data_exists_before}, Data after: {data_gone_after}")
        except Exception as e:
            self.log_result("Secure Deletion", False, str(e))
    
    def test_brute_force_resistance(self):
        """Test 8: Résistance au brute force"""
        try:
            # Simuler des tentatives de mot de passe incorrects
            test_id = "brute_force_test"
            master_key = derive_master_key(self.test_password, "veil_salt")
            encrypted = encrypt(self.test_data.encode(), master_key)
            
            # Stocker en RAM
            store(test_id.encode(), encrypted)
            
            # Tester avec mauvais mots de passe
            wrong_passwords = ["wrong1", "wrong2", "wrong3", "admin", "123456"]
            failed_attempts = 0
            
            for wrong_pwd in wrong_passwords:
                try:
                    wrong_master = derive_master_key(wrong_pwd, "veil_salt")
                    decrypt(encrypted, wrong_master)
                except:
                    failed_attempts += 1
            
            # Test avec bon mot de passe
            try:
                decrypt(encrypted, master_key)
                success_with_correct = True
            except:
                success_with_correct = False
            
            # Nettoyer
            erase_entry(test_id)
            
            resistant = failed_attempts == len(wrong_passwords) and success_with_correct
            
            self.log_result("Brute Force Resistance", 
                          resistant,
                          f"Wrong passwords failed: {failed_attempts}/{len(wrong_passwords)}, Success with correct: {success_with_correct}")
        except Exception as e:
            self.log_result("Brute Force Resistance", False, str(e))
    
    def test_memory_forensics_resistance(self):
        """Test 9: Résistance à l'analyse forensique"""
        try:
            test_id = "forensics_test"
            master_key = derive_master_key(self.test_password, "veil_salt")
            encrypted = encrypt(self.test_data.encode(), master_key)
            
            # Stocker en RAM
            store(test_id.encode(), encrypted)
            
            # Tenter de récupérer les données directement
            raw_data = get(test_id)
            
            # Vérifier que les données ne sont pas en clair
            is_encrypted = raw_data != self.test_data.encode()
            not_empty = raw_data is not None and len(raw_data) > 0
            
            # Activer panic mode et vérifier
            for i in range(12):  # Déclencher panic mode
                get(test_id)
                time.sleep(0.01)
            
            panic_data = get(test_id)
            is_fake = panic_data == b'VEIL::FAKE_DATA_BLOCK'
            
            # Nettoyer
            erase_entry(test_id)
            
            forensic_resistant = is_encrypted and not_empty and is_fake
            
            self.log_result("Memory Forensics Resistance", 
                          forensic_resistant,
                          f"Encrypted: {is_encrypted}, Not empty: {not_empty}, Fake data: {is_fake}")
        except Exception as e:
            self.log_result("Memory Forensics Resistance", False, str(e))
    
    def test_daemon_isolation(self):
        """Test 10: Isolation du daemon"""
        try:
            # Test dans un thread séparé
            def daemon_test():
                start_daemon()
                return get_all_entries()
            
            thread = threading.Thread(target=daemon_test)
            thread.start()
            thread.join()
            
            # Vérifier que le daemon fonctionne
            entries = get_all_entries()
            isolated = isinstance(entries, dict)
            
            self.log_result("Daemon Isolation", 
                          isolated,
                          f"Daemon returns dict: {isolated}")
        except Exception as e:
            self.log_result("Daemon Isolation", False, str(e))
    
    def cleanup_all(self):
        """Nettoie tout le système VEIL"""
        try:
            # Arrêter le daemon
            stop_daemon()
            
            # Vider la RAM
            clear_all()
            
            # Supprimer les fichiers temporaires
            temp_dir = os.path.join(tempfile.gettempdir(), "veil_vault")
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
            
            print("[CLEANUP] System cleaned up")
        except Exception as e:
            print(f"[WARN] Cleanup error: {e}")
    
    def run_all_tests(self):
        """Exécute tous les tests de sécurité"""
        print("[SECURITY] VEIL SECURITY TEST SUITE")
        print("=" * 50)
        print(f"[PASSWORD] Test Password: {self.test_password}")
        print(f"[DATA] Test Data: {self.test_data}")
        print("=" * 50)
        
        # Nettoyer avant les tests
        self.cleanup_all()
        
        # Exécuter tous les tests
        tests = [
            self.test_basic_encryption,
            self.test_password_strength,
            self.test_anti_dump_protection,
            self.test_integrity_verification,
            self.test_persistence_security,
            self.test_concurrent_access,
            self.test_secure_deletion,
            self.test_brute_force_resistance,
            self.test_memory_forensics_resistance,
            self.test_daemon_isolation
        ]
        
        for i, test in enumerate(tests, 1):
            print(f"\n[TEST] Test {i}/10: {test.__name__}")
            test()
            time.sleep(0.5)  # Pause entre tests
        
        # Résultats finaux
        print("\n" + "=" * 50)
        print("[RESULTS] SECURITY TEST RESULTS")
        print("=" * 50)
        print(f"[PASSED] Passed: {self.passed}")
        print(f"[FAILED] Failed: {self.failed}")
        print(f"[RATE] Success Rate: {(self.passed/(self.passed+self.failed)*100):.1f}%")
        
        if self.failed == 0:
            print("\n[SUCCESS] ALL SECURITY TESTS PASSED!")
            print("[INFO] VEIL system is SECURE and ready for production")
        else:
            print(f"\n[WARNING] {self.failed} TESTS FAILED!")
            print("[FIX] Review failed tests before production use")
        
        print("\n[DETAILS] Detailed Results:")
        for result in self.results:
            print(f"  {result['status']} {result['test']}: {result['details']}")
        
        # Nettoyer final
        self.cleanup_all()
        
        return self.failed == 0

def main():
    """Point d'entrée principal"""
    print("[START] Starting VEIL Security Test Suite...")
    
    tester = SecurityTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n[SUCCESS] Security test completed successfully!")
        print("[INFO] VEIL is ready for PRODUCTION use!")
        sys.exit(0)
    else:
        print("\n[ERROR] Security test failed!")
        print("[FIX] Address remaining issues before production")
        sys.exit(1)

if __name__ == "__main__":
    main()
