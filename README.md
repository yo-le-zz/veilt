# veil
Secure in-memory encrypted vault with integrity monitoring, auto-wipe protection, and CLI access for safe inter-process secret management.
Architecture :

src/
│
├── main.py
├── commands.py
├── config.py
│
├── logique/
│   │
│   ├── core.py
│   └── __init__.py
│
└── vault/
    │
    ├── crypto.py
    ├── fake_data.py
    ├── integrity.py
    ├── ram.cpp
    ├── tokens.py
    └── __init__.py