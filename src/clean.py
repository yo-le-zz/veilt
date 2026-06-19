#!/usr/bin/env python3
"""
🧹 VEIL Complete Cleanup Script
Nettoie complètement le système VEIL
"""

import os
import sys
import tempfile
import shutil

def cleanup_vault():
    """Nettoie complètement le système VEIL"""
    print("🧹 VEIL Complete Cleanup")
    print("=" * 40)
    
    try:
        # 1. Arrêter le daemon
        print("1. Arrêt du daemon...")
        try:
            from vault.daemon import stop_daemon
            stop_daemon()
            print("   ✅ Daemon arrêté")
        except Exception as e:
            print(f"   ⚠️ Erreur daemon: {e}")
        
        # 2. Vider la RAM
        print("2. Vidage de la RAM...")
        try:
            from vault.ram import clear_all
            clear_all()
            print("   ✅ RAM vidée")
        except Exception as e:
            print(f"   ⚠️ Erreur RAM: {e}")
        
        # 3. Supprimer les fichiers temporaires
        print("3. Suppression des fichiers temporaires...")
        temp_dir = os.path.join(tempfile.gettempdir(), "veilt_vault")
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                print(f"   ✅ Fichiers temporaires supprimés: {temp_dir}")
            except Exception as e:
                print(f"   ⚠️ Erreur suppression: {e}")
        else:
            print("   ℹ️ Aucun fichier temporaire à supprimer")
        
        # 4. Supprimer la configuration
        print("4. Suppression de la configuration...")
        config_file = "datas/config.json"
        if os.path.exists(config_file):
            try:
                os.remove(config_file)
                print(f"   ✅ Configuration supprimée: {config_file}")
            except Exception as e:
                print(f"   ⚠️ Erreur config: {e}")
        else:
            print("   ℹ️ Aucune configuration à supprimer")
        
        # 5. Nettoyer les logs
        print("5. Nettoyage des logs...")
        log_files = ["datas/logs.json", "datas/"]
        for log_path in log_files:
            if os.path.exists(log_path):
                try:
                    if os.path.isdir(log_path):
                        shutil.rmtree(log_path)
                        print(f"   ✅ Répertoire logs supprimé: {log_path}")
                    else:
                        os.remove(log_path)
                        print(f"   ✅ Fichier log supprimé: {log_path}")
                except Exception as e:
                    print(f"   ⚠️ Erreur logs: {e}")
        
        print("\n🎉 NETTOYAGE COMPLET!")
        print("🛡️ VEIL est maintenant vierge et prêt à être réinitialisé")
        print("\n📋 Prochaines étapes:")
        print("   1. python veilt.py config init --storage ram --password VOTRE_MDP")
        print("   2. python veilt.py add --password VOTRE_MDP --id test --type txt --txt 'test'")
        print("   3. python veilt.py see --password VOTRE_MDP")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR CRITIQUE: {e}")
        return False

def main():
    """Point d'entrée principal"""
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        print("🧹 VEIL Cleanup Script")
        print("Usage: python cleanup_vault.py")
        print("Nettoie complètement le système VEIL")
        return
    
    print("🚀 Démarrage du nettoyage complet de VEIL...")
    
    success = cleanup_vault()
    
    if success:
        print("\n✨ Nettoyage terminé avec succès!")
        sys.exit(0)
    else:
        print("\n💥 Nettoyage échoué!")
        sys.exit(1)

if __name__ == "__main__":
    main()
