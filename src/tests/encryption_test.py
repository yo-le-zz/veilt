#!/usr/bin/env python3
"""
🔐 VEIL Encryption Test Suite
Test complet des fonctionnalités de chiffrement
"""

import os
import sys
import time
import json

# Ajouter le dossier parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import VEIL modules
from vault.crypto import *
from vault.ram import *
from vault.daemon import *
from vault.integrity import *

class EncryptionTester:
    def __init__(self):
        self.test_password = "EncryptTest@2025!"
        self.test_data = "SENSITIVE_ENCRYPTION_TEST_DATA_2025"
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
    
    def test_key_derivation(self):
        """Test 1: Dérivation de clés"""
        try:
            master_key = derive_master_key(self.test_password, "veil_salt")
            entry_key = derive_entry_key(master_key, "test_entry")
            
            # Vérifier que les clés sont différentes
            keys_different = master_key != entry_key
            
            # Vérifier que les clés ne sont pas vides
            master_not_empty = len(master_key) > 0
            entry_not_empty = len(entry_key) > 0
            
            self.log_result("Key Derivation", 
                          keys_different and master_not_empty and entry_not_empty,
                          f"Keys different: {keys_different}, Master not empty: {master_not_empty}")
        except Exception as e:
            self.log_result("Key Derivation", False, str(e))
    
    def test_encryption_decryption(self):
        """Test 2: Chiffrement et déchiffrement"""
        try:
            master_key = derive_master_key(self.test_password, "veil_salt")
            
            # Chiffrement
            original_data = self.test_data.encode()
            encrypted = encrypt(original_data, master_key)
            
            # Déchiffrement
            decrypted = decrypt(encrypted, master_key)
            
            # Vérification
            integrity_check = decrypted == original_data
            string_match = decrypted.decode() == self.test_data
            
            self.log_result("Encryption/Decryption", 
                          integrity_check and string_match,
                          f"Data integrity: {integrity_check}, String match: {string_match}")
        except Exception as e:
            self.log_result("Encryption/Decryption", False, str(e))
    
    def test_integrity_hashing(self):
        """Test 3: Hachage d'intégrité"""
        try:
            master_key = derive_master_key(self.test_password, "veil_salt")
            entry_key = derive_entry_key(master_key, "integrity_test")
            
            # Générer les hashes
            hash1 = hash_data_with_key(self.test_data, entry_key)
            hash2 = hash_data_with_key(self.test_data, entry_key)
            
            # Vérifier la cohérence
            consistent = hash1 == hash2
            
            # Vérifier avec données différentes
            different_data = "DIFFERENT_DATA"
            hash3 = hash_data_with_key(different_data, entry_key)
            different_hash = hash1 != hash3
            
            self.log_result("Integrity Hashing", 
                          consistent and different_hash,
                          f"Consistent: {consistent}, Different data: {different_hash}")
        except Exception as e:
            self.log_result("Integrity Hashing", False, str(e))
    
    def test_storage_retrieval(self):
        """Test 4: Stockage et récupération"""
        try:
            test_id = "storage_test"
            master_key = derive_master_key(self.test_password, "veil_salt")
            
            # Chiffrement
            encrypted = encrypt(self.test_data.encode(), master_key)
            
            # Stockage en RAM
            store(test_id.encode(), encrypted)
            
            # Récupération
            retrieved = get(test_id)
            
            # Vérification
            data_match = retrieved == encrypted
            
            # Nettoyage
            erase_entry(test_id)
            
            self.log_result("Storage & Retrieval", 
                          data_match,
                          f"Data match: {data_match}")
        except Exception as e:
            self.log_result("Storage & Retrieval", False, str(e))
    
    def test_persistence_encryption(self):
        """Test 5: Persistance avec chiffrement"""
        try:
            # Nettoyer
            stop_daemon()
            clear_all()
            
            test_id = "persistence_enc_test"
            master_key = derive_master_key(self.test_password, "veil_salt")
            
            # Chiffrement
            encrypted = encrypt(self.test_data.encode(), master_key)
            
            # Stockage avec persistance
            start_daemon()
            register_entry(test_id, "test_hash", encrypted)
            
            # Vérifier la persistance
            from vault.daemon import _load_data
            retrieved_data = _load_data(test_id)
            
            persistence_works = retrieved_data == encrypted
            
            self.log_result("Persistence Encryption", 
                          persistence_works,
                          f"Data persisted correctly: {persistence_works}")
        except Exception as e:
            self.log_result("Persistence Encryption", False, str(e))
    
    def test_multiple_entries(self):
        """Test 6: Gestion de multiples entrées"""
        try:
            master_key = derive_master_key(self.test_password, "veil_salt")
            
            # Créer plusieurs entrées
            entries = {}
            for i in range(5):
                entry_id = f"multi_test_{i}"
                data = f"Test data {i}"
                encrypted = encrypt(data.encode(), master_key)
                
                store(entry_id.encode(), encrypted)
                entries[entry_id] = encrypted
            
            # Récupérer toutes les entrées
            all_retrieved = True
            for entry_id, original_data in entries.items():
                retrieved = get(entry_id)
                if retrieved != original_data:
                    all_retrieved = False
                    break
            
            # Nettoyer
            for entry_id in entries.keys():
                erase_entry(entry_id)
            
            self.log_result("Multiple Entries", 
                          all_retrieved,
                          f"All entries retrieved: {all_retrieved}")
        except Exception as e:
            self.log_result("Multiple Entries", False, str(e))
    
    def test_large_data(self):
        """Test 7: Gestion de données volumineuses"""
        try:
            master_key = derive_master_key(self.test_password, "veil_salt")
            
            # Créer des données volumineuses (1MB)
            large_data = "A" * (1024 * 1024)  # 1MB de 'A'
            
            # Chiffrement
            encrypted = encrypt(large_data.encode(), master_key)
            
            # Stockage et récupération
            test_id = "large_data_test"
            store(test_id.encode(), encrypted)
            retrieved = get(test_id)
            
            # Vérification
            data_match = retrieved == encrypted
            size_correct = len(retrieved) == len(encrypted)
            
            # Nettoyage
            erase_entry(test_id)
            
            self.log_result("Large Data Handling", 
                          data_match and size_correct,
                          f"Data match: {data_match}, Size correct: {size_correct}")
        except Exception as e:
            self.log_result("Large Data Handling", False, str(e))
    
    def test_concurrent_encryption(self):
        """Test 8: Chiffrement concurrent"""
        try:
            import threading
            from concurrent.futures import ThreadPoolExecutor
            
            master_key = derive_master_key(self.test_password, "veil_salt")
            
            results = []
            errors = []
            
            def encrypt_data(data_id):
                try:
                    data = f"Concurrent test {data_id}"
                    encrypted = encrypt(data.encode(), master_key)
                    results.append((data_id, encrypted))
                except Exception as e:
                    errors.append(str(e))
            
            # Chiffrement concurrent
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(encrypt_data, i) for i in range(10)]
                for future in futures:
                    future.result()
            
            # Vérifier la cohérence
            all_success = len(results) == 10 and len(errors) == 0
            unique_encryptions = len(set([enc for _, enc in results])) == 10
            
            self.log_result("Concurrent Encryption", 
                          all_success and unique_encryptions,
                          f"All success: {all_success}, Unique encryptions: {unique_encryptions}")
        except Exception as e:
            self.log_result("Concurrent Encryption", False, str(e))
    
    def test_error_handling(self):
        """Test 9: Gestion d'erreurs"""
        try:
            master_key = derive_master_key(self.test_password, "veil_salt")
            
            # Test avec mauvaises données
            error_cases = []
            
            # Cas 1: Données corrompues
            try:
                decrypt(b"corrupted_data", master_key)
            except:
                error_cases.append("corrupted_data_handled")
            
            # Cas 2: Clé incorrecte
            try:
                wrong_key = derive_master_key("wrong_password", "veil_salt")
                decrypt(encrypt(self.test_data.encode(), master_key), wrong_key)
            except:
                error_cases.append("wrong_key_handled")
            
            # Cas 3: Entrée inexistante
            try:
                get("nonexistent_entry")
            except:
                error_cases.append("nonexistent_handled")
            
            all_errors_handled = len(error_cases) == 3
            
            self.log_result("Error Handling", 
                          all_errors_handled,
                          f"Error cases handled: {len(error_cases)}/3")
        except Exception as e:
            self.log_result("Error Handling", False, str(e))
    
    def test_performance(self):
        """Test 10: Performance de chiffrement"""
        try:
            master_key = derive_master_key(self.test_password, "veil_salt")
            
            # Test de performance
            test_data = "Performance test data " * 100  # ~2KB
            
            # Mesurer le temps de chiffrement
            start_time = time.time()
            for _ in range(100):
                encrypted = encrypt(test_data.encode(), master_key)
                decrypt(encrypted, master_key)
            end_time = time.time()
            
            total_time = end_time - start_time
            avg_time = total_time / 100
            
            # Performance acceptable (< 10ms par opération)
            performance_good = avg_time < 0.01
            
            self.log_result("Encryption Performance", 
                          performance_good,
                          f"Average time: {avg_time*1000:.2f}ms, Good performance: {performance_good}")
        except Exception as e:
            self.log_result("Encryption Performance", False, str(e))
    
    def cleanup(self):
        """Nettoie après les tests"""
        try:
            clear_all()
            stop_daemon()
            print("[CLEANUP] Encryption tests cleaned up")
        except:
            pass
    
    def run_all_tests(self):
        """Exécute tous les tests de chiffrement"""
        print("[ENCRYPTION] VEIL ENCRYPTION TEST SUITE")
        print("=" * 50)
        print(f"[PASSWORD] Test Password: {self.test_password}")
        print(f"[DATA] Test Data: {self.test_data[:50]}...")
        print("=" * 50)
        
        # Exécuter tous les tests
        tests = [
            self.test_key_derivation,
            self.test_encryption_decryption,
            self.test_integrity_hashing,
            self.test_storage_retrieval,
            self.test_persistence_encryption,
            self.test_multiple_entries,
            self.test_large_data,
            self.test_concurrent_encryption,
            self.test_error_handling,
            self.test_performance
        ]
        
        for i, test in enumerate(tests, 1):
            print(f"\n[TEST] Test {i}/10: {test.__name__}")
            test()
            time.sleep(0.2)  # Pause entre tests
        
        # Résultats finaux
        print("\n" + "=" * 50)
        print("[RESULTS] ENCRYPTION TEST RESULTS")
        print("=" * 50)
        print(f"[PASSED] Passed: {self.passed}")
        print(f"[FAILED] Failed: {self.failed}")
        print(f"[RATE] Success Rate: {(self.passed/(self.passed+self.failed)*100):.1f}%")
        
        if self.failed == 0:
            print("\n[SUCCESS] ALL ENCRYPTION TESTS PASSED!")
            print("VEIL encryption system is robust and secure")
        else:
            print(f"\n[WARNING] {self.failed} TESTS FAILED!")
            print("[FIX] Review encryption implementation")
        
        print("\n[DETAILS] Detailed Results:")
        for result in self.results:
            print(f"  {result['status']} {result['test']}: {result['details']}")
        
        # Nettoyer final
        self.cleanup()
        
        return self.failed == 0

def main():
    """Point d'entrée principal"""
    print("[START] Starting VEIL Encryption Test Suite...")
    
    tester = EncryptionTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n[SUCCESS] Encryption test completed successfully!")
        print("[INFO] VEIL encryption is production-ready!")
        sys.exit(0)
    else:
        print("\n[ERROR] Encryption test failed!")
        print("[FIX] Address encryption issues before production")
        sys.exit(1)

if __name__ == "__main__":
    main()
