# 🛡️ VEIL - Military-Grade Secure In-Memory Vault

**VEIL** is a high-security, military-grade in-memory vault system designed for temporary, encrypted storage of sensitive data with advanced anti-forensic capabilities, PyMem protection, and comprehensive integrity monitoring.

## 🚨 **NEW FEATURES - v1.0.0**

- 🛡️ **Anti-PyMem Protection** - Detects and blocks memory hacking tools
- 🚨 **Panic Mode** - Automatic fake data injection on suspicious activity  
- 📊 **Attack Monitoring** - Real-time logging of security threats
- 🔍 **Integrity Verification** - SHA-256 data corruption detection
- 💾 **Secure Persistence** - Encrypted temporary file storage
- 🎯 **Memory Attack Testing** - Built-in penetration testing suite

## 🏗️ Architecture Overview

VEIL consists of 6 interconnected systems working together to provide secure, temporary storage with full audit trails:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI Layer     │    │   CRYPTO        │    │   RAM ENGINE    │
│                 │    │                 │    │                 │
│ veil add/get    │◄──►│ password → hash │◄──►│ C++ Storage     │
│ see/del/commands│    │ key derivation  │    │ anti-dump       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   DAEMON        │    │   LOG SYSTEM    │    │   INTEGRITY     │
│                 │    │                 │    │                 │
│ Global INDEX    │◄──►│ Event history   │◄──►│Data verification│
│ Status tracking │    │ Reasons         │    │ Corruption      │
│ Crash detection │    │ Runtime logs    │    │ detection       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔧 System Components

### A. CRYPTO System (`vault/crypto.py`)
**Role**: Cryptographic operations and key management

- **Password Hashing**: SHA-256 for master password storage
- **Key Derivation**: PBKDF2-HMAC-SHA256 (150,000 iterations)
- **Master Key**: Derived from password + salt
- **Entry Keys**: Unique keys per entry from master key + entry ID
- **Encryption**: Fernet (AES-128-CBC + HMAC-SHA256)
- **Integrity Hashing**: SHA-256 of data + key combination

### B. RAM ENGINE (`native/ram/ram.cpp`)
**Role**: Low-level, secure in-memory storage

- **Thread-Safe Storage**: Mutex-protected unordered_map
- **Anti-Dump Protection**: 
  - Access pattern monitoring
  - Rapid access detection (< 100ms)
  - Frequency limits (> 10 accesses)
  - Panic mode activation
- **Secure Wipe**: Multi-pass overwrite (0x00 → 0xFF)
- **Fake Responses**: Returns dummy data when suspicious activity detected
- **Memory Tracking**: Access counters and timestamps

### C. WRAPPER (`vault/ram.py`)
**Role**: Python interface to native DLL

- **ctypes Integration**: Clean Python bindings
- **Type Safety**: Proper argument/return type definitions
- **Error Handling**: Graceful fallbacks for DLL failures
- **Functions**: `store()`, `get()`, `erase_entry()`, `clear_all()`, `is_panic_mode()`

### D. DAEMON (`vault/daemon.py`)
**Role**: Global state management and monitoring

- **Entry Status Tracking**: ACTIVE, DELETED, CRASHED, CORRUPTED
- **Global INDEX**: Central metadata registry
- **Crash Detection**: Automatic detection of RAM inconsistencies
- **Background Sync**: Persistent storage to temp directory
- **Thread Safety**: Daemon-wide locking mechanisms

### E. LOG SYSTEM (`vault/logs.py`)
**Role**: Comprehensive audit trail and event tracking

- **Event Types**: Creation, access, deletion, crashes, auth failures
- **Delete Reasons**: User request, auth failure, integrity mismatch, panic
- **Structured Logging**: JSON format with timestamps
- **Log Analysis**: Entry-specific logs, crash summaries
- **Persistence**: Temporary file storage with rotation

### F. INTEGRITY (`vault/integrity.py`)
**Role**: Data verification and corruption detection

- **Multi-layer Verification**: Basic hash + HMAC + structure checks
- **Corruption Analysis**: Detailed breakdown of corruption types
- **Integrity Reports**: Comprehensive data health assessments
- **Secure Comparison**: Constant-time hash verification
- **Error Classification**: Encoding, size, and tampering detection

## 🚀 Complete Data Flow

### Adding Data (`veil add`)
```
1. CLI receives command + password + data
2. CRYPTO derives master key → entry key
3. CRYPTO encrypts data with master key
4. INTEGRITY generates data hash with entry key
5. RAM ENGINE stores encrypted data
6. DAEMON registers entry in global INDEX
7. LOG SYSTEM records creation event
```

### Retrieving Data (`veil get`)
```
1. CLI requests data with password
2. RAM ENGINE checks panic mode status
3. RAM ENGINE returns encrypted data
4. CRYPTO derives keys and decrypts data
5. INTEGRITY verifies data integrity
6. DAEMON updates access counters
7. LOG SYSTEM records access event
```

### Deleting Data (`veil del`)
```
1. CLI requests deletion
2. RAM ENGINE securely wipes data (multi-pass)
3. DAEMON updates entry status to DELETED
4. LOG SYSTEM records deletion with reason
5. Access counters and metadata cleaned up
```

## 🛡️ Security Features

### Anti-Dump System
- **Access Monitoring**: Tracks frequency and timing of accesses
- **Panic Mode**: Automatic activation on suspicious patterns
- **Fake Data**: Returns dummy information when triggered
- **Memory Protection**: Prevents forensic analysis

### Integrity Protection
- **Multi-layer Hashing**: Basic + keyed + structural verification
- **Tamper Detection**: Immediate corruption identification
- **Secure Comparison**: Constant-time operations
- **Audit Trail**: Complete event logging

### Secure Deletion
- **Multi-pass Wipe**: 0x00 → 0xFF overwrite patterns
- **Metadata Cleanup**: Complete entry removal
- **Access Tracking**: Secure counter clearing
- **Status Updates**: Proper DELETED state marking

## 📊 Entry Status System

| Status | Description | Trigger |
|--------|-------------|---------|
| 🟢 ACTIVE | Entry is valid and accessible | Normal operation |
| 🔴 DELETED | Entry was securely deleted | User request or system action |
| 💥 CRASHED | Entry lost from RAM | Crash detection or RAM wipe |
| ⚠️ CORRUPTED | Entry data is corrupted | Integrity check failure |

## 🔍 Monitoring & Visibility

### `veil see` Command
Provides comprehensive system visibility:

**System Overview**:
- Total entries count
- RAM entries vs INDEX entries
- Panic mode status
- Crash summary statistics

**Entry Details**:
- Creation and access timestamps
- Access frequency tracking
- Current status and reason
- Recent event history

**Log Analysis**:
- Delete reasons (auth fail, integrity mismatch, etc.)
- Crash detection events
- Anti-dump triggers
- Authentication failures

## 🚨 Anti-Forensic Features

### Panic Mode Triggers:
- Rapid successive accesses (< 100ms intervals)
- High frequency access (> 10 times)
- Invalid authentication attempts
- Integrity verification failures
- Manual activation

### Panic Mode Behavior:
- All `get()` operations return fake data
- New `store()` operations are silently rejected
- System logs panic trigger event
- Maintains normal appearance to attackers

### Secure Wipe:
- Multi-pass memory overwriting
- Complete metadata cleanup
- Access counter clearing
- INDEX entry removal

## 📋 Command Reference

### 🚀 Quick Start

```bash
# 1. Initialize VEIL
python veil.py config init --storage ram --password "YourSecurePassword123!" --ram-limit 512mo --disk-limit 1gb

# 2. Add sensitive data
python veil.py add --password "YourSecurePassword123!" --id "secret_note" --type txt --txt "This is a secret message"

# 3. Retrieve data
python veil.py get --id "secret_note" --password "YourSecurePassword123!"

# 4. Check status and monitor attacks
python veil.py see --password "YourSecurePassword123!" --attack

# 5. Verify integrity
python veil.py integrity --password "YourSecurePassword123!"

# 6. Secure cleanup
python veil.py purge
```

## 📋 **Complete Command Reference**

### 🔧 **Configuration**
```bash
veil config init --storage ram --password "PASS" --ram-limit 512mo --disk-limit 1gb
veil config get
veil config set --storage ram --password "PASS"
```

### 📦 **Data Management**
```bash
veil add --password "PASS" --id "secret1" --type txt --txt "Secret text"
veil add --password "PASS" --id "file1" --type file --file "document.txt"
veil get --id "secret1" --password "PASS"
veil del --id "secret1" [--force]
```

### 🔍 **Monitoring & Security**
```bash
veil see --password "PASS" [--id "specific_id"] [--attack]
veil integrity --password "PASS" [--id "specific_id"]
veil purge
```

### 🎯 **Testing Suite**
```bash
cd tests
python memory_test.py          # Memory attack simulation
python encryption_test.py      # Cryptography tests  
python security_test.py         # Security validation
python run_tests.py            # Full test suite
```

## �️ **Advanced Security Features**

### 🔥 **Anti-PyMem Protection**
VEIL includes advanced protection against memory hacking tools like PyMem:

```python
# Automatic threat detection
threat_report = scan_threats()
# Detects: PyMem, debuggers, memory anomalies, suspicious imports

# Real-time monitoring
python veil.py see --password "PASS" --attack
# Shows: Attack attempts, threat level, suspicious activity
```

**Protection Features:**
- 🚨 **PyMem Detection** - Scans for memory hacking libraries
- 🔍 **Debugger Detection** - Identifies attached debuggers
- 📊 **Memory Anomaly Detection** - Unusual allocation patterns
- 🚫 **Automatic Blocking** - Denies access when threats detected
- 📋 **Attack Logging** - Complete audit trail of attempts

### 🚨 **Panic Mode System**
When suspicious activity is detected, VEIL automatically enters panic mode:

```bash
# Rapid access triggers panic mode
for i in range(50):
    data = get("secret_id")  # Triggers after ~10 rapid accesses
    # Returns: "VEIL::FAKE_DATA_BLOCK"
```

**Panic Mode Features:**
- 🎭 **Fake Data Injection** - Returns dummy data to attackers
- 🛡️ **Access Blocking** - Denies all further access attempts
- 📊 **Threat Logging** - Records attack details
- 🔁 **Auto-Recovery** - Returns to normal after cooldown

### 🔍 **Attack Monitoring Dashboard**
```bash
python veil.py see --password "PASS" --attack
```

**Dashboard Shows:**
- 🛡️ **Protection Status** - Anti-PyMem enabled/disabled
- 🚨 **Panic Mode** - Current panic state
- 📊 **Threat Level** - LOW/MEDIUM/HIGH/CRITICAL
- 📋 **Attack History** - Recent attack attempts
- 📁 **Temp Files** - Monitored storage files
- 🔐 **System Integrity** - Overall health status

## � Installation & Setup

### Prerequisites
- Python 3.8+
- Microsoft Visual Studio (for C++ compilation)
- Required Python packages: `typer`, `cryptography`, `rich`

### Compilation
```bash
cd src/native/ram
# Use provided compile script or manual compilation
```

### Installation
```bash
# Install dependencies
pip install typer cryptography rich

# Run tests to verify installation
python src/tests/run_tests.py
```
Data Encryption
```

### Threat Model
- **Memory Dumping**: Protected by anti-dump system
- **Forensic Analysis**: Fake data responses and secure wipe
- **Brute Force**: Rate limiting and panic mode
- **Integrity Attacks**: Multi-layer verification
- **Timing Attacks**: Constant-time operations

### Failure Modes
- **Graceful Degradation**: System continues with reduced functionality
- **Secure Defaults**: Fail-safe to protect data
- **Audit Preservation**: Logs maintained even during failures
- **Recovery Mechanisms**: Crash detection and status tracking

## 📝 Logging & Auditing

### Event Types
- `ENTRY_CREATED`: New data added
- `ENTRY_ACCESSED`: Data retrieval attempts
- `ENTRY_DELETED`: Secure deletion events
- `ENTRY_CRASHED`: Crash detection
- `AUTH_FAILED`: Authentication failures
- `INTEGRITY_MISMATCH`: Corruption detection
- `PANIC_TRIGGERED`: Anti-dump activation
- `ANTI_DUMP_TRIGGERED`: Suspicious access patterns

### Delete Reasons
- `USER_REQUEST`: Manual deletion
- `AUTH_FAILURE`: Too many failed attempts
- `INTEGRITY_MISMATCH`: Data corruption detected
- `PANIC_WIPE`: System panic mode
- `ANTI_DUMP`: Forensic protection triggered
- `CRASH_RECOVERY`: Post-crash cleanup

## 🔄 Data Lifecycle

1. **Creation**: Encrypted storage with integrity verification
2. **Access**: Authenticated retrieval with audit logging
3. **Monitoring**: Continuous integrity and access pattern analysis
4. **Deletion**: Secure wipe with complete metadata cleanup
5. **Recovery**: Crash detection and status reconciliation

## 🛠️ Development Notes

### Thread Safety
- All components use proper locking mechanisms
- Daemon provides global synchronization
- RAM engine uses mutex protection
- Log operations are atomic

### Error Handling
- Graceful degradation on failures
- Comprehensive error logging
- User-friendly error messages
- Secure fallback behaviors

### Performance Considerations
- In-memory operations for speed
- Minimal disk I/O (only for persistence)
- Efficient cryptographic operations
- Optimized data structures

---

**VEIL** provides military-grade security for temporary data storage with comprehensive monitoring, anti-forensic capabilities, and complete audit trails. Perfect for handling sensitive information that needs to be stored securely and wiped completely.