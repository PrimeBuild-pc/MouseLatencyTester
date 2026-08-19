"""Translation layer.

Every language is a flat JSON file in :data:`LOCALES_DIR`.  Adding one means
dropping ``xx.json`` next to the others and adding a display name to
:data:`LANGUAGE_NAMES` -- no Python changes, no build step, no dependency.

Missing keys fall back to English and then to the key itself, so a partial or
outdated translation degrades instead of crashing.

Serial protocol tokens (TRIG, LAT, ARMED, REARM, CALIB_OK, BTN1:PRESS, ...) are
NEVER translated: they belong to the wire format, not to the interface.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable

log = logging.getLogger(__name__)

FALLBACK_LANGUAGE = "en"
LOCALES_DIR = Path(__file__).parent / "locales"

#: Display names are written in their own language, as users expect to see them.
LANGUAGE_NAMES = {
    "en": "English",
    "it": "Italiano",
    "de": "Deutsch",
    "es": "Español",
    "fr": "Français",
    "ja": "日本語",
    "ru": "Русский",
    "zh": "中文",
}


def _load_locales() -> dict[str, dict[str, str]]:
    tables: dict[str, dict[str, str]] = {}
    for path in sorted(LOCALES_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            log.warning("skipping locale %s: %s", path.name, exc)
            continue
        if isinstance(data, dict):
            tables[path.stem] = {k: str(v) for k, v in data.items()}
    if FALLBACK_LANGUAGE not in tables:
        raise RuntimeError(f"missing required locale {FALLBACK_LANGUAGE}.json")
    return tables


TRANSLATIONS: dict[str, dict[str, str]] = _load_locales()


class Translator:
    """Holds the active language and resolves keys."""

    def __init__(self, language: str = "en"):
        self._language = FALLBACK_LANGUAGE
        self._observers: list[Callable[[str], None]] = []
        self.language = language

    @property
    def language(self) -> str:
        return self._language

    @language.setter
    def language(self, value: str) -> None:
        self._language = value if value in TRANSLATIONS else FALLBACK_LANGUAGE

    def available(self) -> dict[str, str]:
        """``{code: display name}`` for every locale actually present."""
        return {code: LANGUAGE_NAMES.get(code, code) for code in sorted(TRANSLATIONS)}

    def subscribe(self, callback: Callable[[str], None]) -> None:
        """Register a callback fired when the language changes."""
        self._observers.append(callback)

    def set_language(self, value: str) -> None:
        previous = self._language
        self.language = value
        if self._language != previous:
            for callback in list(self._observers):
                callback(self._language)

    def __call__(self, key: str, **params: object) -> str:
        text = (TRANSLATIONS.get(self._language, {}).get(key)
                or TRANSLATIONS[FALLBACK_LANGUAGE].get(key)
                or key)
        if params:
            try:
                return text.format(**params)
            except (KeyError, IndexError, ValueError):
                return text
        return text


#: Process-wide translator.  The app swaps its language from the settings tab.
translator = Translator()
t = translator
