# 🛡️ VEIL

**Coffre-fort chiffré, sécurisé, en mémoire et/ou sur disque, pour Python — installable via `pip` et utilisable dans n'importe quel projet avec un simple mot de passe.**

**Secure, encrypted, in-memory and/or on-disk vault for Python — `pip`-installable and usable in any project with just a password.**

[![PyPI](https://img.shields.io/pypi/v/veil-vault)](https://pypi.org/project/veil-vault/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platforms](https://img.shields.io/badge/platforms-Windows%20%7C%20Linux%20%7C%20ARM%20(Raspberry%20Pi)-blue)]()

Author / Auteur: **yolezz**

---

## 🇫🇷 Présentation

VEIL est une librairie Python (avec moteur natif C++) qui fournit un coffre-fort
chiffré pour vos secrets (clés API, tokens, mots de passe, identifiants...).
Elle s'installe avec `pip install veil-vault` et s'utilise dans n'importe quel
script avec un simple mot de passe — sans serveur, sans dépendance externe
obligatoire.

```python
import veil

with veil.Vault(password="Mon-Mot-De-Passe-Solide!") as vault:
    vault.set("api_key", "sk-xxxxxxxx")
    print(vault.get("api_key"))
```

### Pourquoi cette version 1.0.0 ?

Ce dépôt a été entièrement reconstruit à partir du prototype initial. L'objectif
était de transformer un script de démonstration en une vraie librairie sécurisée,
multiplateforme et publiable sur PyPI. Voir [`CHANGELOG.md`](CHANGELOG.md) pour le
détail complet, et la section [Bugs corrigés](#-bugs-corrigés--bugs-fixed) ci-dessous.

### Inspirations (sans copier leur architecture)

- **HashiCorp Vault** : modèle seal/unseal, journal d'audit en chaîne de hachage
  inviolable, secrets à durée de vie (TTL/lease) — réimplémentés localement,
  sans serveur ni réseau.
- **Windows Credential Manager** : intégration native (ctypes, zéro dépendance)
  pour stocker un jeton de déverrouillage rapide, optionnel.
- **macOS Keychain / `keyring`** : même principe sur Linux via la librairie
  optionnelle `keyring` (Secret Service / KWallet).

VEIL reste néanmoins un **composant local intégrable**, pas un service : tout
tient dans votre processus Python.

---

## 🇬🇧 Overview

VEIL is a Python library (with a native C++ engine) providing an encrypted
vault for your secrets (API keys, tokens, passwords, credentials...). Install
it with `pip install veil-vault` and use it in any script with just a
password — no server, no mandatory external dependency.

```python
import veil

with veil.Vault(password="My-Strong-Password!") as vault:
    vault.set("api_key", "sk-xxxxxxxx")
    print(vault.get("api_key"))
```

---

## 📦 Installation

```bash
pip install veil-vault

# Optional extras
pip install "veil-vault[keyring]"   # OS-native secret store on Linux/macOS
pip install "veil-vault[windows]"   # extra privilege-elevation hardening on Windows
```

VEIL ships prebuilt wheels (Windows x64, Linux x86_64, Linux ARM64 — including
the **Raspberry Pi 5**). If no wheel matches your platform, `pip` compiles the
native extension from source automatically (any C++17 compiler works).

If the native extension cannot be built at all on some unusual platform, VEIL
falls back transparently to a pure-Python engine with the exact same API
(reduced memory-locking protection only — see [`memory.py`](src/veil/memory.py)).

---

## 🚀 Démarrage rapide / Quickstart

### En tant que librairie / As a library

```python
import veil

# Crée le coffre au premier usage, le déverrouille ensuite
with veil.Vault(password="P@ssw0rd-Solide!42", storage="disk") as vault:
    vault.set("github_token", "ghp_xxxxxxxxxxxx")
    vault.set("db_password", "s3cr3t", ttl=3600)  # auto-expire après 1h

    token = vault.get("github_token")
    print(vault.status())

# One-liners façon `keyring`
veil.quick_set("token", "abc", password="...")
token = veil.quick_get("token", password="...")
```

### En ligne de commande / Command line

```bash
veil --lang fr config init --name default --storage disk
veil add api_key "sk-xxxx" --name default --storage disk
veil get api_key --name default --storage disk
veil see --name default --storage disk
veil integrity api_key --name default --storage disk
veil audit verify --name default --storage disk
veil del api_key --name default --storage disk
veil purge --name default --yes
```

Évitez `--password` en ligne de commande (visible dans l'historique du shell) :
préférez la saisie interactive ou la variable d'environnement `VEIL_PASSWORD`.

Avoid `--password` on the command line (visible in shell history): prefer the
interactive prompt or the `VEIL_PASSWORD` environment variable.

### Mode administrateur / Admin mode

```bash
veil --admin config init --name default --storage disk
```

```python
from veil import elevate
if not elevate.is_admin():
    elevate.request_admin()  # relance le process avec UAC/sudo, puis quitte
vault = veil.Vault(password="...", admin=True)
```

Le mode admin/root débloque : verrouillage mémoire illimité (mlock/VirtualLock
sans quota), durcissement anti-dump renforcé, stockage système (`/etc/veil` ou
`%PROGRAMDATA%\Veil`). **VEIL ne s'élève jamais tout seul** — c'est toujours un
appel explicite.

---

## 🏗️ Architecture

```
┌──────────────┐   ┌───────────────┐   ┌──────────────────┐
│   CLI (FR/EN)│──▶│  veil.Vault   │──▶│  veil.crypto      │
│  Typer + Rich│   │  (façade)     │   │  Argon2id+AES-GCM │
└──────────────┘   └───────┬───────┘   └──────────────────┘
                            │
        ┌───────────────┬──┴───┬────────────────┬─────────────┐
        ▼                ▼     ▼                 ▼             ▼
  veil.memory      veil.daemon  veil.logs   veil.integrity  veil.antimem
  (native C++       (TTL/status  (audit       (HMAC layer)   (threat
   engine + mlock/   leases)      hash-chain)                 scanning)
   VirtualLock)
        │
        ▼
  veil._veil_native (pybind11, compiled per-platform: Windows/Linux/ARM)
```

| Module | Rôle / Role |
|---|---|
| `veil.vault` | API publique haut niveau (`Vault`) / High-level public API |
| `veil.crypto` | Argon2id (hash + KDF) + AES-256-GCM + HKDF |
| `veil.native` (C++) | Stockage mémoire verrouillée, anti-dump, panic mode |
| `veil.memory` | Pont natif ↔ repli Python pur / native ↔ pure-Python fallback bridge |
| `veil.integrity` | Couche HMAC indépendante (défense en profondeur) |
| `veil.logs` | Journal d'audit en chaîne de hachage inviolable |
| `veil.daemon` | Statuts d'entrées, TTL/lease, en thread d'arrière-plan |
| `veil.antimem` | Détection d'outils d'inspection mémoire |
| `veil.osvault` | Intégration optionnelle Windows Credential Manager / `keyring` |
| `veil.elevate` | Détection/élévation de privilèges admin / root |
| `veil.config` | Emplacements XDG/AppData cross-plateforme |
| `veil.i18n` | Traduction FR/EN |

---

## 🔐 Sécurité cryptographique / Cryptography

| | v1.0.0 (actuel) | Ancien prototype |
|---|---|---|
| Hash du mot de passe | **Argon2id** (memory-hard) | SHA-256 brut |
| Dérivation de clé | **Argon2id**, sel unique stocké par coffre | PBKDF2-SHA256, 150k itérations |
| Chiffrement | **AES-256-GCM** (AEAD authentifié) | Fernet (AES-128-CBC + HMAC) |
| Intégrité | Tag GCM intégré **+** HMAC-SHA256 indépendant (optionnel, activé par défaut) | SHA-256 simple |
| Clés dérivées | HKDF, une clé indépendante par usage (chiffrement / HMAC / audit) | Clé unique réutilisée partout |

---

## 🧠 Sécurité mémoire / Memory security

- Chaque secret est stocké dans un buffer **verrouillé en RAM** (`mlock` sur
  Linux, `VirtualLock` sur Windows) : interdiction au système d'exploitation de
  le swapper sur disque.
- Le processus est durci contre les core dumps (`prctl(PR_SET_DUMPABLE, 0)` +
  `RLIMIT_CORE=0` sous Linux).
- Toute mémoire libérée est **réécrite (zeroed)** avant d'être rendue à l'OS.
- Un secret reste en mémoire **aussi longtemps que le process tourne et que
  vous n'appelez pas `delete()`/`close()`** — des heures si nécessaire. Ceci
  s'applique à l'usage librairie dans un process long-vivant (`storage="ram"`).
  En usage CLI, chaque commande est un nouveau processus : utilisez
  `storage="disk"` (chiffré au repos) pour la persistance entre appels.
- En mode `--admin`/`admin=True`, la limite de verrouillage mémoire
  (`RLIMIT_MEMLOCK`) est levée et les privilèges Windows
  `SeLockMemoryPrivilege` sont activés (nécessite `pywin32`, extra `[windows]`).

---

## 🚨 Mode panique / Panic mode

Le moteur natif détecte les schémas d'accès suspects (lectures trop rapprochées,
trop nombreuses) et bascule en mode panique : il renvoie des **données leurres**
plutôt que d'échouer bruyamment ou de continuer à exposer le vrai secret. Une
réinitialisation explicite (`reset_panic()`) est nécessaire après revue du
journal d'audit.

---

## ✅ Bugs corrigés / Bugs fixed

Issus du commentaire d'aide fourni et de l'analyse du code source original :

1. **Mode panique cassé (logique de timing)** — `LAST_ACCESS[key]` était écrasé
   *avant* le calcul de `time_diff`, rendant le délai mesuré quasi nul à chaque
   lecture, déclenchant le mode panique presque systématiquement. **Corrigé** :
   l'ancien timestamp est capturé avant l'écrasement
   (`src/veil/native/engine.cpp`).
2. **Pointeur pendouillant (dangling pointer)** — `get()` retournait un
   `const char*` pointant directement dans le vecteur de stockage, *après*
   libération du mutex : une autre thread pouvait invalider ce pointeur entre
   temps. **Corrigé** : la copie en `py::bytes` est faite *pendant* que le
   mutex est tenu.
3. **Troncature sur octet NUL** — l'ancienne interface `ctypes`/`c_char_p`
   tronquait silencieusement toute donnée binaire contenant un octet `0x00`,
   ce qu'un ciphertext AES-GCM contient régulièrement. **Corrigé** : utilisation
   systématique de `py::bytes`/`std::string` à longueur explicite.
4. **Sel codé en dur** — le code original appelait
   `derive_master_key(password, "veil_salt")` avec une chaîne littérale au lieu
   du sel aléatoire réellement stocké par coffre, annulant l'intérêt du sel.
   **Corrigé** : `Vault` charge systématiquement `config["salt"]`.
5. **Crypto faible** — SHA-256 brut + PBKDF2 + Fernet remplacés par
   Argon2id + AES-256-GCM (voir tableau ci-dessus).
6. **État global partagé** — `daemon.py`/`antimem.py` utilisaient des variables
   de module globales, provoquant des collisions entre plusieurs instances dans
   un même process. **Corrigé** : classes instanciées par `Vault`.
7. **Chemin de données fixe sans droits d'écriture** — risque de
   `PermissionError` selon la plateforme/l'installation. **Corrigé** :
   résolution automatique d'un répertoire utilisateur inscriptible
   (XDG/AppData), avec emplacement système uniquement en mode admin explicite.

---

## 🧪 Tests

```bash
pip install -e ".[dev]"
pytest -v
```

---

## 🛠️ Build

```bash
# Wheel / sdist (pip)
python -m build

# Exécutable autonome Windows + Linux, en parallèle, logs préfixés
python tools/compileur.py
```

Voir [`tools/compileur.py`](tools/compileur.py) : construit la plateforme hôte
localement (vrai build Nuitka) et déclenche automatiquement le job GitHub
Actions correspondant pour l'autre plateforme (Nuitka n'est pas un
cross-compilateur).

---

## 📄 Licence

MIT — voir [`LICENSE`](LICENSE). © 2026 yolezz.
