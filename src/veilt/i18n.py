"""
veilt.i18n
==========
Minimal FR/EN translation engine for CLI and log-facing messages.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict

_LOCALES_DIR = Path(__file__).parent / "locales"
_CACHE: Dict[str, Dict[str, str]] = {}
_current_lang = os.environ.get("VEIL_LANG", "fr").lower()
if _current_lang not in ("fr", "en"):
    _current_lang = "fr"


def _load(lang: str) -> Dict[str, str]:
    if lang not in _CACHE:
        path = _LOCALES_DIR / f"{lang}.json"
        if not path.exists():
            path = _LOCALES_DIR / "en.json"
        with open(path, "r", encoding="utf-8") as f:
            _CACHE[lang] = json.load(f)
    return _CACHE[lang]


def set_language(lang: str) -> None:
    global _current_lang
    lang = (lang or "en").lower()
    _current_lang = lang if lang in ("fr", "en") else "en"


def get_language() -> str:
    return _current_lang


def t(key: str, **kwargs) -> str:
    """Translate `key` into the current language. Falls back to English,
    then to the raw key itself, so a missing translation never crashes."""
    table = _load(_current_lang)
    text = table.get(key) or _load("en").get(key) or key
    try:
        return text.format(**kwargs)
    except (KeyError, IndexError):
        return text
