#!/usr/bin/env python3
"""
🚀 VEIL Test Runner
Script simple pour lancer tous les tests VEIL
"""

import os
import sys
import subprocess

def run_command(cmd, description):
    """Exécute une commande et affiche le résultat"""
    print(f"\n[TEST] {description}")
    print("=" * 50)
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("[OK] Commande exécutée avec succès")
            if result.stdout:
                print(result.stdout)
        else:
            print("[ERROR] Erreur lors de l'exécution")
            if result.stderr:
                print(f"[ERROR] Erreur: {result.stderr}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"[ERROR] Erreur: {e}")
        return False

def main():
    """Point d'entrée principal"""
    print("[RUNNER] VEIL Test Runner")
    print("Ce script exécute tous les tests de validation VEIL")
    print("=" * 60)
    
    # Obtenir le répertoire actuel
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    
    # Liste des tests à exécuter
    tests = [
        {
            "cmd": f'cd "{parent_dir}" && python veilt.py purge',
            "desc": "Nettoyage complet du système VEIL"
        },
        {
            "cmd": f'cd "{parent_dir}" && python veilt.py config init --storage ram --password "TestSecure123!" --ram-limit 512mo --disk-limit 1gb',
            "desc": "Initialisation de la configuration VEIL"
        },
        {
            "cmd": f'cd "{parent_dir}" && python veilt.py add --password "TestSecure123!" --id "test_data" --type txt --txt "DONNEES_SENSIBLES_TEST_2025"',
            "desc": "Ajout de données de test"
        },
        {
            "cmd": f'cd "{parent_dir}" && python veilt.py see --password "TestSecure123!"',
            "desc": "Vérification des données stockées"
        },
        {
            "cmd": f'cd "{parent_dir}" && python veilt.py get --id "test_data" --password "TestSecure123!"',
            "desc": "Récupération des données"
        },
        {
            "cmd": f'cd "{parent_dir}" && python veilt.py del --id "test_data"',
            "desc": "Suppression sécurisée des données"
        },
        {
            "cmd": f'cd "{current_dir}" && python memory_test.py',
            "desc": "Test d'accès mémoire VEIL"
        },
        {
            "cmd": f'cd "{current_dir}" && python encryption_test.py',
            "desc": "Test de chiffrement VEIL"
        },
        {
            "cmd": f'cd "{current_dir}" && python security_test.py',
            "desc": "Test de sécurité complet VEIL"
        }
    ]
    
    # Exécuter tous les tests
    results = []
    for i, test in enumerate(tests, 1):
        print(f"\n[STEP] TEST {i}/{len(tests)}: {test['desc']}")
        success = run_command(test['cmd'], test['desc'])
        results.append((test['desc'], success))
    
    # Résultats finaux
    print("\n" + "=" * 60)
    print("[RESULTS] RÉSULTATS FINAUX DES TESTS")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    failed = len(results) - passed
    
    for desc, success in results:
        status = "[OK] SUCCÈS" if success else "[ERROR] ÉCHEC"
        print(f"{status} {desc}")
    
    print(f"\n[STATS] Réussite: {passed}/{len(results)} ({passed/len(results)*100:.1f}%)")
    print(f"[FAILED] Échecs: {failed}/{len(results)}")
    
    if failed == 0:
        print("\n[SUCCESS] TOUS LES TESTS RÉUSSIS!")
        print("[INFO] VEIL est prêt pour la production!")
        sys.exit(0)
    else:
        print(f"\n[WARNING] {failed} TESTS ONT ÉCHOUÉ!")
        print("[FIX] Corrigez les problèmes avant la production")
        sys.exit(1)

if __name__ == "__main__":
    main()
