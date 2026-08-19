"""Every shipped locale must be complete and safe to format.

These run over the JSON files themselves, so a contributor adding a language
gets told exactly what is wrong before it ever reaches the interface.
"""

import json
import re
import string

import pytest

from latency_tester import i18n

PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")
REQUIRED = ("en", "it", "de", "es", "fr", "ja", "ru", "zh")

LOCALE_CODES = sorted(i18n.TRANSLATIONS)
ENGLISH = i18n.TRANSLATIONS["en"]


def placeholders(text: str) -> set[str]:
    return set(PLACEHOLDER_RE.findall(text))


def test_all_advertised_languages_ship():
    assert set(REQUIRED) <= set(LOCALE_CODES)


def test_every_locale_has_a_display_name():
    for code in LOCALE_CODES:
        assert code in i18n.LANGUAGE_NAMES, f"{code} has no entry in LANGUAGE_NAMES"


@pytest.mark.parametrize("code", LOCALE_CODES)
def test_locale_file_is_valid_json_of_strings(code):
    path = i18n.LOCALES_DIR / f"{code}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert all(isinstance(v, str) for v in data.values())


@pytest.mark.parametrize("code", LOCALE_CODES)
def test_locale_defines_exactly_the_english_keys(code):
    keys = set(i18n.TRANSLATIONS[code])
    english = set(ENGLISH)
    assert not english - keys, f"{code} is missing: {sorted(english - keys)}"
    assert not keys - english, f"{code} has unknown keys: {sorted(keys - english)}"


@pytest.mark.parametrize("code", LOCALE_CODES)
def test_placeholders_match_english(code):
    """A translated string that renames {path} to {ruta} would silently render
    the untranslated fallback -- catch it here instead."""
    for key, english_text in ENGLISH.items():
        translated = i18n.TRANSLATIONS[code][key]
        assert placeholders(translated) == placeholders(english_text), (
            f"{code}:{key} placeholders differ from English")


@pytest.mark.parametrize("code", LOCALE_CODES)
def test_every_string_formats_without_raising(code):
    """No stray braces: `{` in a translation must be a real placeholder."""
    formatter = string.Formatter()
    for key, text in i18n.TRANSLATIONS[code].items():
        try:
            list(formatter.parse(text))
        except ValueError as exc:  # pragma: no cover - only on a bad locale
            pytest.fail(f"{code}:{key} is not a valid format string: {exc}")


@pytest.mark.parametrize("code", LOCALE_CODES)
def test_no_value_is_empty(code):
    for key, text in i18n.TRANSLATIONS[code].items():
        assert text.strip(), f"{code}:{key} is empty"


@pytest.mark.parametrize("code", LOCALE_CODES)
def test_protocol_tokens_are_never_translated(code):
    """Wire-format tokens must survive verbatim in every language."""
    table = i18n.TRANSLATIONS[code]
    # These appear inside UI strings and must stay exactly as the firmware
    # prints them.
    assert "LAT {value}" in table["log.latency"]
    assert "TRIG" in table["log.trig_unmatched"]
    assert "BTN1/BTN2" in table["tip.buttons"]
    # And no key may itself be a token.
    for token in ("TRIG", "ARMED", "REARM", "TESTMODE:ON", "SKIP:OLED_REFRESH",
                  "BTN1:PRESS", "BTN2:PRESS", "CALIB_OK"):
        assert token not in table, f"{token} must not be a UI key"


@pytest.mark.parametrize("code", LOCALE_CODES)
def test_translator_resolves_every_key_in_every_language(code):
    translator = i18n.Translator(code)
    for key in ENGLISH:
        assert translator(key) != key or key == ENGLISH[key], (
            f"{code}:{key} resolved to the raw key")


def test_switching_through_every_language_works():
    translator = i18n.Translator("en")
    seen = set()
    for code in LOCALE_CODES:
        translator.set_language(code)
        assert translator.language == code
        seen.add(translator("tab.live"))
    # Languages should not all render identically.
    assert len(seen) > 1
