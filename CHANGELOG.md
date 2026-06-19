# Changelog

All notable changes to this project are documented here.

## [1.0.0] — 2026-06-19

Complete rebuild of the original prototype into a real, pip-installable,
cross-platform (Windows / Linux / ARM) security library.

### Added
- `pip install veil-vault` — installable as a library (`import veil`) and a
  CLI (`veil`), with prebuilt wheels for Windows x64, Linux x86_64, and
  Linux ARM64 (Raspberry Pi 5).
- Native secure-memory engine rewritten in pybind11 (`veil._veil_native`),
  cross-compiling natively for Windows/Linux/ARM via the normal `pip install`
  build, replacing the old single-platform `ram.dll` + `ctypes` design.
- Pure-Python fallback engine (`veil.memory`) used automatically if no C++
  compiler is available at install time.
- Argon2id password hashing + key derivation, AES-256-GCM authenticated
  encryption, HKDF-derived independent sub-keys.
- Optional, independent HMAC-SHA256 integrity layer (defense in depth on top
  of AES-GCM's own authentication).
- Tamper-evident, hash-chained audit log (`veil.logs`), inspired by
  HashiCorp Vault's audit guarantees, fully local.
- TTL / lease support on individual entries (`vault.set(..., ttl=...)`).
- Cross-platform secure memory locking: `mlock` (Linux) / `VirtualLock`
  (Windows), process anti-dump hardening (`prctl(PR_SET_DUMPABLE)`,
  `RLIMIT_CORE=0`), secure zero-on-free for every secret buffer.
- `--admin` / `admin=True` elevated mode: unrestricted memory locking,
  system-wide storage location, stronger hardening. Never elevates silently.
- Optional OS-native secret store integration (`veil.osvault`): zero-dependency
  Windows Credential Manager bindings, optional `keyring` backend on
  Linux/macOS - used only for an optional quick-unlock token, never for the
  vault's actual secrets.
- FR/EN CLI and log messages (`veil.i18n`, `--lang fr|en`).
- Cross-platform, XDG/AppData-compliant data directories (`veil.config`) -
  always resolves a writable per-user location by default.
- Full pytest suite (crypto, native engine incl. fallback, vault, integrity).
- `tools/compileur.py`: parallel-threaded Windows + Linux standalone
  executable builder with live, clearly prefixed progress, dispatching to
  GitHub Actions for the platform that can't be cross-compiled locally.
- GitHub Actions CI (multi-OS / multi-Python test matrix) and release
  workflow (cibuildwheel wheels incl. manylinux_aarch64, PyPI publish on tag,
  Nuitka standalone executables).

### Fixed (see README "Bugs corrigés / Bugs fixed" for details)
- Panic-mode timing logic read `LAST_ACCESS` after it had already been
  overwritten, making the measured elapsed time ~0ms and triggering panic
  mode on virtually every second read.
- `get()` returned a raw pointer into the storage vector *after* releasing
  the mutex - a dangling-pointer race with concurrent `erase_entry()`/
  `clear_all()` calls.
- The `ctypes`/`c_char_p` interface silently truncated any binary data
  containing an embedded NUL byte (routine for real AES-GCM ciphertext).
- `derive_master_key(password, "veil_salt")` used a hardcoded literal salt
  instead of the actual per-vault random salt stored in config, defeating
  the salt entirely.
- Module-level global state in the daemon/anti-memory-scan modules caused
  multiple instances in the same process to silently collide.
- Fixed data paths writing to locations without guaranteed write permission;
  VEIL now always resolves a writable per-user directory by default.

### Changed
- SHA-256 password hashing → Argon2id.
- PBKDF2-HMAC-SHA256 (150k iterations) → Argon2id (memory-hard KDF).
- Fernet (AES-128-CBC + HMAC) → AES-256-GCM (AEAD).
- Single reused key for everything → HKDF-derived independent sub-keys per
  purpose (encryption / HMAC integrity / audit chain).
