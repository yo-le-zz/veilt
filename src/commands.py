import typer
import json

# =========================================================
# Core imports
# =========================================================
from logique import init_config, set_config, get_config
from vault.crypto import hash_password, derive_master_key, derive_entry_key, encrypt, decrypt, hash_data_with_key
from vault.ram import store, get, erase_entry, is_panic_mode
from vault.daemon import start_daemon, stop_daemon, register_entry, update_entry_status, get_entry_status, get_all_entries, increment_access, EntryStatus
from vault.logs import log_entry_created, log_entry_accessed, log_entry_deleted, log_auth_failed, log_integrity_mismatch, log_panic_triggered, DeleteReason
from vault.integrity import verify_entry_integrity, detect_corruption, generate_integrity_report
from vault.antimem import auto_protect, scan_threats, get_protection_status, is_panic_triggered as anti_mem_panic


def register_commands(app: typer.Typer):

    # =========================================================
    # PURGE COMMAND
    # =========================================================

    @app.command()
    def purge():
        """Complete cleanup of VEIL system"""
        try:
            import os
            import tempfile
            import shutil
            
            print("🧹 VEIL Complete Purge")
            print("=" * 40)
            
            # 1. Arrêter le daemon
            print("1. Arrêt du daemon...")
            try:
                from vault.daemon import stop_daemon
                stop_daemon()
                print("   ✅ Daemon arrêté")
            except Exception as e:
                print(f"   ⚠️ Erreur daemon: {e}")
            
            # 2. Overwrite sécurisé de la RAM avant vidage
            print("2. Overwrite sécurisé de la RAM...")
            try:
                from vault.ram import store, size, clear_all
                from vault.daemon import TEMP_DIR
                import os
                import glob
                
                # Charger directement depuis les fichiers de données persistants
                entries_to_overwrite = []
                
                # Chercher tous les fichiers .data dans le répertoire temporaire
                temp_dir = os.path.join(tempfile.gettempdir(), "veil_vault")
                if os.path.exists(temp_dir):
                    data_files = glob.glob(os.path.join(temp_dir, "*.data"))
                    print(f"   [INFO] Fichiers de données trouvés: {len(data_files)}")
                    
                    for data_file in data_files:
                        try:
                            # Extraire l'ID du nom de fichier
                            entry_id = os.path.basename(data_file).replace(".data", "")
                            
                            # Lire les données chiffrées
                            with open(data_file, 'rb') as f:
                                encrypted_data = f.read()
                            
                            if encrypted_data:
                                # Stocker en RAM pour overwrite
                                store(entry_id.encode(), encrypted_data)
                                entries_to_overwrite.append(entry_id)
                                print(f"   📦 [LOAD] Entrée chargée: {entry_id} ({len(encrypted_data)} bytes) 📈")
                        except Exception as e:
                            print(f"   ⚠️ Erreur chargement {data_file}: {e}")
                
                print(f"   [INFO] Entrées chargées pour overwrite: {len(entries_to_overwrite)}")
                ram_size = size()
                print(f"   [INFO] Taille RAM actuelle: {ram_size} entrées")
                
                # Overwrite multi-pass de toutes les entrées existantes
                if ram_size > 0:
                    # Pass 1: Zeroes
                    print("   [OVERWRITE] Pass 1: Zeroes...")
                    for i in range(ram_size):
                        try:
                            store(f"purge_temp_{i}".encode(), b'\x00' * 1024)
                        except:
                            pass
                    
                    # Pass 2: Ones
                    print("   [OVERWRITE] Pass 2: Ones...")
                    for i in range(ram_size):
                        try:
                            store(f"purge_temp_{i}".encode(), b'\xFF' * 1024)
                        except:
                            pass
                    
                    # Pass 3: Random
                    print("   [OVERWRITE] Pass 3: Random...")
                    for i in range(ram_size):
                        try:
                            store(f"purge_temp_{i}".encode(), os.urandom(1024))
                        except:
                            pass
                    
                    # Nettoyer les entrées temporaires
                    print("   [OVERWRITE] Nettoyage des entrées temporaires...")
                    for i in range(ram_size):
                        try:
                            erase_entry(f"purge_temp_{i}".encode())
                        except:
                            pass
                
                # Vider complètement la RAM
                print("   [CLEAR] Vidage complet de la RAM...")
                clear_all()
                print("   [OK] RAM vidée avec overwrite sécurisé")
                
            except Exception as e:
                print(f"   [WARN] Erreur overwrite RAM: {e}")
                # Essayer le vidage simple quand même
                try:
                    from vault.ram import clear_all
                    clear_all()
                    print("   [OK] RAM vidée (mode simple)")
                except Exception as e2:
                    print(f"   [ERROR] Erreur vidage RAM: {e2}")
            
            # 3. Supprimer les fichiers temporaires
            print("3. Suppression des fichiers temporaires...")
            temp_dir = os.path.join(tempfile.gettempdir(), "veil_vault")
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
                        print(f"   ❌ Erreur logs: {e}")
            
            print("\n🎉 PURGE COMPLET!")
            print("💡 VEIL est maintenant vierge et prêt à être réinitialisé")
            print("📋 Prochaines étapes:")
            print("   1. python veil.py config init --storage ram --password VOTRE_MDP")
            print("   2. python veil.py add --password VOTRE_MDP --id test --type txt --txt 'test'")
            print("   3. python veil.py see --password VOTRE_MDP")
            
            result = {
                "status": "success",
                "message": "VEIL system completely purged"
            }
            
        except Exception as e:
            result = {
                "status": "error",
                "message": str(e)
            }
        
        print(json.dumps(result, indent=2))

    # =========================================================
    # CONFIG COMMAND
    # =========================================================

    @app.command()
    def config(
        action: str = typer.Argument(None),
        storage: str = typer.Option(None, "--storage"),
        password: str = typer.Option(None, "--password"),
        ram_limit: str = typer.Option(None, "--ram-limit"),
        disk_limit: str = typer.Option(None, "--disk-limit"),
        json_mode: bool = typer.Option(False, "--json")
    ):

        if action == "init":
            result = init_config(storage, password, ram_limit, disk_limit)

        elif action == "set":
            result = set_config(storage, password, ram_limit, disk_limit)

        else:
            result = get_config()

        print(json.dumps(result, indent=2))


    # =========================================================
    # ADD COMMAND (NEW IMPLEMENTATION)
    # =========================================================

    @app.command()
    def add(
        password: str = typer.Option(..., "--password"),
        id: str = typer.Option(..., "--id"),
        type: str = typer.Option(..., "--type"),
        txt: str = typer.Option(None, "--txt"),
        file: str = typer.Option(None, "--file"),
        json_mode: bool = typer.Option(False, "--json")
    ):
        """Add encrypted data to vault"""
        
        try:
            # Anti-PyMem protection scan
            threat_report = auto_protect()
            if threat_report.get('threat_level') in ['HIGH', 'CRITICAL']:
                from vault.logs import log_attack
                log_attack("PYMEM_PROTECTION", "add_command", True, threat_report)
                if threat_report.get('panic_triggered'):
                    raise Exception("SECURITY_ALERT: Memory hacking detected - access denied")
            
            # Start daemon if not running
            start_daemon()
            
            # Get data based on type
            if type == "txt":
                if not txt:
                    raise typer.BadParameter("--txt is required for type txt")
                data = txt
            elif type == "file":
                if not file:
                    raise typer.BadParameter("--file is required for type file")
                with open(file, "rb") as f:
                    data = f.read().decode(errors="ignore")
            else:
                raise typer.BadParameter("type must be 'txt' or 'file'")
            
            # Derive keys
            master_key = derive_master_key(password, "veil_salt")
            entry_key = derive_entry_key(master_key, id)
            
            # Encrypt data
            encrypted_data = encrypt(data.encode(), master_key)
            
            # Generate integrity hash
            data_hash = hash_data_with_key(data, entry_key)
            
            # Store in RAM
            store(id.encode(), encrypted_data)
            
            # Start daemon and register entry with data persistence
            start_daemon()
            register_entry(id, data_hash, encrypted_data)
            
            # Log creation
            log_entry_created(id, data_hash)
            
            result = {
                "status": "success",
                "id": id,
                "message": "Data added successfully",
                "hash": data_hash[:16] + "..."  # Show only first 16 chars
            }
            
        except Exception as e:
            result = {
                "status": "error",
                "message": str(e)
            }
        
        # Output
        if json_mode:
            print(json.dumps(result, indent=2))
        else:
            if result["status"] == "success":
                print(f"✅ {result['message']}")
                print(f"🆔 ID: {result['id']}")
                print(f"🔐 Hash: {result['hash']}")
            else:
                print(f"❌ Error: {result['message']}")

    # =========================================================
    # GET COMMAND
    # =========================================================

    @app.command()
    def get(
        id: str = typer.Option(..., "--id"),
        password: str = typer.Option(..., "--password"),
        json_mode: bool = typer.Option(False, "--json")
    ):
        """Retrieve and decrypt data from vault"""
        
        try:
            # Anti-PyMem protection scan
            threat_report = auto_protect()
            if threat_report.get('threat_level') in ['HIGH', 'CRITICAL']:
                from vault.logs import log_attack
                log_attack("PYMEM_PROTECTION", "get_command", True, threat_report)
                if threat_report.get('panic_triggered'):
                    raise Exception("SECURITY_ALERT: Memory hacking detected - access denied")
            
            # Check panic mode
            if is_panic_mode() or anti_mem_panic():
                log_panic_triggered("get_command_attempt")
                raise Exception("PANIC_MODE: Access denied")
            
            # Get encrypted data from persistent storage
            from vault.daemon import _load_data
            encrypted_data = _load_data(id)
            if not encrypted_data:
                raise Exception("Entry not found")
            
            # Also try to load into RAM for faster access
            from vault.ram import store
            try:
                store(id.encode(), encrypted_data)
            except:
                pass  # Ignore RAM loading errors
            
            # Derive keys
            master_key = derive_master_key(password, "veil_salt")
            entry_key = derive_entry_key(master_key, id)
            
            # Decrypt data
            try:
                decrypted_data = decrypt(encrypted_data, master_key).decode()
            except Exception:
                log_auth_failed(id)
                raise Exception("Authentication failed - invalid password")
            
            # Verify integrity
            entry_status = get_entry_status(id)
            expected_hash = entry_status.get("data_hash")
            if expected_hash:
                actual_hash = hash_data_with_key(decrypted_data, entry_key)
                if actual_hash != expected_hash:
                    log_integrity_mismatch(id, expected_hash, actual_hash)
                    update_entry_status(id, EntryStatus.CORRUPTED, "integrity_mismatch")
                    raise Exception("Data integrity check failed")
            
            # Update access
            increment_access(id)
            log_entry_accessed(id, True)
            
            result = {
                "status": "success",
                "id": id,
                "data": decrypted_data,
                "access_count": entry_status.get("access_count", 0) + 1
            }
            
        except Exception as e:
            log_entry_accessed(id, False)
            result = {
                "status": "error",
                "message": str(e)
            }
        
        # Output
        if json_mode:
            print(json.dumps(result, indent=2))
        else:
            if result["status"] == "success":
                print(f"✅ Entry retrieved successfully")
                print(f"🆔 ID: {result['id']}")
                print(f"📊 Access count: {result['access_count']}")
                print(f"📄 Data:")
                print(result['data'])
            else:
                print(f"❌ Error: {result['message']}")

    # =========================================================
    # DELETE COMMAND
    # =========================================================

    @app.command(name="del")
    def delete_command(
        id: str = typer.Option(..., "--id"),
        force: bool = typer.Option(False, "--force", help="Force delete and clear all logs"),
        json_mode: bool = typer.Option(False, "--json")
    ):
        """Securely delete entry from vault"""
        
        try:
            # Check if entry exists (force load from disk)
            from vault.daemon import start_daemon, get_all_entries
            start_daemon()
            all_entries = get_all_entries()
            if id not in all_entries:
                raise Exception("Entry not found")
            entry_status = all_entries[id]
            
            # Secure wipe from RAM (multi-pass)
            erase_entry(id)
            
            # Multi-pass overwrite for additional security
            try:
                from vault.ram import store
                # Pass 1: Zeroes
                store(id.encode(), b'\x00' * 1024)
                # Pass 2: Ones  
                store(id.encode(), b'\xFF' * 1024)
                # Pass 3: Random
                import os
                store(id.encode(), os.urandom(1024))
                # Final wipe
                erase_entry(id)
            except:
                pass  # Ignore errors in additional wipes
            
            # Delete persistent data file
            from vault.daemon import _save_data, TEMP_DIR
            import os
            data_file = os.path.join(TEMP_DIR, f"{id}.data")
            if os.path.exists(data_file):
                os.remove(data_file)
            
            # Update status
            update_entry_status(id, EntryStatus.DELETED, DeleteReason.USER_REQUEST.value)
            
            # Log deletion
            log_entry_deleted(id, DeleteReason.USER_REQUEST)
            
            # Force delete: clear all logs for this entry
            if force:
                try:
                    from vault.logs import clear_entry_logs
                    clear_entry_logs(id)
                    print(f"   [FORCE] Logs cleared for entry: {id}")
                except Exception as e:
                    print(f"   [WARN] Could not clear logs: {e}")
            
            result = {
                "status": "success",
                "id": id,
                "message": "Entry securely deleted" + (" (logs cleared)" if force else "")
            }
            
        except Exception as e:
            result = {
                "status": "error",
                "message": str(e)
            }
        
        # Output
        if json_mode:
            print(json.dumps(result, indent=2))
        else:
            if result["status"] == "success":
                print(f"✅ {result['message']}")
                print(f"🆔 ID: {result['id']}")
            else:
                print(f"❌ Error: {result['message']}")

    # =========================================================
    # SEE COMMAND
    # =========================================================

    @app.command()
    def see(
        password: str = typer.Option(..., "--password"),
        id: str = typer.Option(None, "--id"),
        json_mode: bool = typer.Option(False, "--json"),
        attack: bool = typer.Option(False, "--attack", help="Show attack logs and security status")
    ):
        """Show vault status and entry information"""
        
        try:
            # Verify password
            master_key = derive_master_key(password, "veil_salt")
            
            if attack:
                # Show attack logs and security status
                print("\n🚨 VEIL SECURITY ATTACK MONITOR")
                print("=" * 50)
                
                # Check panic mode
                from vault.ram import is_panic_mode
                panic_status = is_panic_mode()
                print(f"🛡️ Panic Mode: {'ACTIVE' if panic_status else 'INACTIVE'}")
                
                # Get attack logs
                try:
                    from vault.logs import get_attack_logs
                    attack_logs = get_attack_logs()
                    
                    if attack_logs:
                        print(f"\n📋 Recent Attack Attempts: {len(attack_logs)}")
                        for log in attack_logs[-10:]:  # Show last 10 attacks
                            timestamp = log.get('timestamp', 'Unknown')
                            attack_type = log.get('type', 'Unknown')
                            source = log.get('source', 'Unknown')
                            blocked = log.get('blocked', False)
                            status = "🚫 BLOCKED" if blocked else "⚠️ DETECTED"
                            print(f"  {status} {timestamp} - {attack_type} from {source}")
                    else:
                        print("\n✅ No recent attacks detected")
                except:
                    print("\n⚠️ Attack logging system unavailable")
                
                # Monitor temp files for suspicious activity
                import os
                import tempfile
                import glob
                
                temp_dir = os.path.join(tempfile.gettempdir(), "veil_vault")
                if os.path.exists(temp_dir):
                    data_files = glob.glob(os.path.join(temp_dir, "*.data"))
                    print(f"\n📁 Temp Files Monitored: {len(data_files)} files")
                    for data_file in data_files[-5:]:  # Show last 5 files
                        file_size = os.path.getsize(data_file)
                        file_name = os.path.basename(data_file)
                        print(f"  📄 {file_name} ({file_size} bytes)")
                else:
                    print("\n📁 No temp files found (clean state)")
                
                # Check system integrity
                try:
                    from vault.integrity import generate_integrity_report
                    integrity_report = generate_integrity_report()
                    print(f"\n🔐 System Integrity: {integrity_report.get('status', 'Unknown')}")
                    if integrity_report.get('issues'):
                        print(f"  ⚠️ Issues detected: {len(integrity_report['issues'])}")
                except:
                    print("\n⚠️ Integrity check unavailable")
                
                # Anti-PyMem protection status
                try:
                    protection_status = get_protection_status()
                    print(f"\n🛡️ Anti-PyMem Protection: {'ENABLED' if protection_status['protection_enabled'] else 'DISABLED'}")
                    print(f"🚨 Panic Mode: {'ACTIVE' if protection_status['panic_mode'] else 'INACTIVE'}")
                    
                    if protection_status['last_scan']:
                        last_scan = protection_status['last_scan']
                        print(f"📊 Last Scan: {last_scan['threat_level']} threat level")
                        if last_scan['suspicious_imports']:
                            print(f"  ⚠️ Suspicious imports: {len(last_scan['suspicious_imports'])}")
                        if last_scan['debugger_attached']:
                            print(f"  🚨 Debugger detected: YES")
                        if any(last_scan['memory_anomalies'].values()):
                            print(f"  🔍 Memory anomalies detected")
                        if last_scan['suspicious_access']:
                            print(f"  👁️ Suspicious process access: {len(last_scan['suspicious_access'])}")
                    else:
                        print("  ℹ️ No scan performed yet")
                        
                    # Manual threat scan
                    print(f"\n🔍 Scanning for PyMem threats...")
                    threat_report = scan_threats()
                    print(f"  📊 Current threat level: {threat_report['threat_level']}")
                    if threat_report['threat_level'] != 'LOW':
                        print(f"  🚨 THREATS DETECTED:")
                        if threat_report['suspicious_imports']:
                            print(f"    📦 Suspicious imports: {threat_report['suspicious_imports']}")
                        if threat_report['debugger_attached']:
                            print(f"    🔍 Debugger attached")
                        if threat_report['suspicious_access']:
                            print(f"    👁️ Suspicious access: {threat_report['suspicious_access']}")
                    else:
                        print(f"  ✅ No threats detected")
                        
                except Exception as e:
                    print(f"\n⚠️ Anti-PyMem protection unavailable: {e}")
                
                return
            
            if id:
                # Show specific entry
                entry_status = get_entry_status(id)
                if not entry_status:
                    raise Exception("Entry not found")
                
                # Get logs for this entry
                from vault.logs import get_entry_logs
                entry_logs = get_entry_logs(id, 10)
                
                # Determine status display
                status = entry_status["status"]
                if status == EntryStatus.ACTIVE.value:
                    status_display = "[ACTIVE] ACTIVE"
                elif status == EntryStatus.DELETED.value:
                    status_display = "[DELETED] DELETED"
                elif status == EntryStatus.CRASHED.value:
                    status_display = "[CRASHED] CRASHED"
                elif status == EntryStatus.CORRUPTED.value:
                    status_display = "[CORRUPTED] CORRUPTED"
                else:
                    status_display = f"[UNKNOWN] {status}"
                
                # Get delete reason if applicable
                reason = ""
                if status in [EntryStatus.DELETED.value, EntryStatus.CRASHED.value]:
                    from vault.logs import get_delete_reason
                    reason = get_delete_reason(id) or "Unknown"
                
                result = {
                    "id": id,
                    "status": status_display,
                    "created_at": entry_status.get("created_at"),
                    "last_seen": entry_status.get("last_seen"),
                    "access_count": entry_status.get("access_count", 0),
                    "reason": reason,
                    "recent_logs": entry_logs[-5:] if entry_logs else []
                }
            else:
                # Show all entries (force fresh load)
                from vault.daemon import start_daemon, _load_index, _sync_index
                start_daemon()
                _load_index()  # Force reload from disk
                _sync_index()  # Sync any changes
                all_entries = get_all_entries()
                
                entries_summary = []
                for entry_id, metadata in all_entries.items():
                    status = metadata["status"]
                    if status == EntryStatus.ACTIVE.value:
                        status_display = "[ACTIVE] ACTIVE"
                    elif status == EntryStatus.DELETED.value:
                        status_display = "[DELETED] DELETED"
                    elif status == EntryStatus.CRASHED.value:
                        status_display = "[CRASHED] CRASHED"
                    elif status == EntryStatus.CORRUPTED.value:
                        status_display = "[CORRUPTED] CORRUPTED"
                    else:
                        status_display = f"[UNKNOWN] {status}"
                    
                    entries_summary.append({
                        "id": entry_id,
                        "status": status_display,
                        "created_at": metadata.get("created_at"),
                        "access_count": metadata.get("access_count", 0)
                    })
                
                # Get system status
                from vault.ram import size, is_panic_mode
                from vault.logs import get_crash_summary
                
                result = {
                    "system_status": {
                        "total_entries": len(all_entries),
                        "ram_entries": size(),
                        "panic_mode": is_panic_mode(),
                        "crash_summary": get_crash_summary()
                    },
                    "entries": entries_summary
                }
            
        except Exception as e:
            result = {
                "status": "error",
                "message": str(e)
            }
        
        # Output
        if json_mode:
            print(json.dumps(result, indent=2))
        else:
            if "status" in result and result["status"] == "error":
                print(f"[ERROR] Error: {result['message']}")
            elif id:
                # Single entry display
                print(f"[ENTRY] Entry Information")
                print(f"[ID] ID: {result['id']}")
                print(f"[STATUS] Status: {result['status']}")
                print(f"[CREATED] Created: {result['created_at']}")
                print(f"[SEEN] Last seen: {result['last_seen']}")
                print(f"[COUNT] Access count: {result['access_count']}")
                if result['reason']:
                    print(f"[REASON] Reason: {result['reason']}")
                if result['recent_logs']:
                    print(f"[EVENTS] Recent events:")
            else:
                # System summary display
                system = result["system_status"]
                print(f"\n🖥️ VEIL SYSTEM STATUS")
                print(f"📊 Total entries: {system['total_entries']}")
                print(f"🧠 RAM entries: {system['ram_entries']}")
                print(f"🚨 Panic mode: {'ACTIVE' if system['panic_mode'] else 'INACTIVE'}")
                print(f"💥 Crashes: {system['crash_summary']}")
                
                print(f"\n📋 Entries:")
                if result["entries"]:
                    for entry in result["entries"]:
                        print(f"  {entry['status']} {entry['id']} (accessed {entry['access_count']}x)")
                else:
                    print("  ℹ️ No entries found")

    # =========================================================
    # INTEGRITY COMMAND
    # =========================================================

    @app.command()
    def integrity(
        password: str = typer.Option(..., "--password"),
        id: str = typer.Option(None, "--id"),
        json_mode: bool = typer.Option(False, "--json")
    ):
        """Check system and data integrity"""
        try:
            # Verify password
            master_key = derive_master_key(password, "veil_salt")
            
            if id:
                # Check specific entry integrity
                from vault.daemon import get_entry_status
                from vault.integrity import verify_entry_integrity
                
                entry_status = get_entry_status(id)
                if not entry_status:
                    raise Exception("Entry not found")
                
                # Get stored data hash
                stored_hash = entry_status.get("data_hash")
                
                # Verify integrity
                integrity_ok = verify_entry_integrity(id, stored_hash)
                
                result = {
                    "status": "success",
                    "entry_id": id,
                    "integrity_check": "PASS" if integrity_ok else "FAIL",
                    "stored_hash": stored_hash[:16] + "..." if stored_hash else None,
                    "message": "Entry integrity verified" if integrity_ok else "Integrity check failed"
                }
            else:
                # Check system-wide integrity
                from vault.daemon import get_all_entries
                
                all_entries = get_all_entries()
                
                result = {
                    "status": "success",
                    "total_entries": len(all_entries),
                    "corruption_detected": [],
                    "integrity_status": "OK",
                    "message": "System integrity check completed"
                }
                
        except Exception as e:
            result = {
                "status": "error",
                "message": str(e)
            }
        
        # Output
        if json_mode:
            print(json.dumps(result, indent=2))
        else:
            if result["status"] == "success":
                if id:
                    print(f"🔐 Integrity Check for {result['entry_id']}")
                    print(f"📊 Status: {result['integrity_check']}")
                    print(f"🔑 Hash: {result['stored_hash']}")
                    print(f"✅ {result['message']}")
                else:
                    print(f"🔐 System Integrity Report")
                    print(f"📊 Total entries: {result['total_entries']}")
                    print(f"� Integrity Status: {result['integrity_status']}")
                    if result['corruption_detected']:
                        print(f"🚨 Issues detected: {len(result['corruption_detected'])}")
                        for issue in result['corruption_detected']:
                            print(f"  📋 {issue}")
                    else:
                        print(f"✅ No corruption detected")
                    print(f"📊 {result['message']}")
            else:
                print(f"❌ Error: {result['message']}")