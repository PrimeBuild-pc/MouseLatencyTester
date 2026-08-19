import json

from latency_tester import i18n
from latency_tester.settings import DEFAULTS, Settings


# ------------------------------------------------------------- settings ----
def test_defaults_are_used_when_no_file_exists(tmp_path):
    settings = Settings(tmp_path / "settings.json")
    assert settings.get("language") == DEFAULTS["language"]
    assert settings.get("theme") == "system"


def test_settings_round_trip(tmp_path):
    path = tmp_path / "settings.json"
    settings = Settings(path)
    settings.set("theme", "dark")
    settings.set("language", "en")
    settings.set("last_device_id", 3)
    settings.save()

    reloaded = Settings(path)
    assert reloaded.get("theme") == "dark"
    assert reloaded.get("language") == "en"
    assert reloaded.get("last_device_id") == 3


def test_unknown_keys_in_the_file_are_preserved(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"future_option": 42}), encoding="utf-8")
    settings = Settings(path)
    settings.set("theme", "light")
    settings.save()
    assert json.loads(path.read_text(encoding="utf-8"))["future_option"] == 42


def test_a_corrupt_file_falls_back_to_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{not json", encoding="utf-8")
    settings = Settings(path)
    assert settings.get("theme") == DEFAULTS["theme"]


def test_data_dir_override(tmp_path):
    settings = Settings(tmp_path / "settings.json")
    settings.set("data_dir", str(tmp_path / "archive"))
    assert settings.db_path == tmp_path / "archive" / "latency_tester.db"


def test_env_override_for_the_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("LATENCY_TESTER_HOME", str(tmp_path / "portable"))
    from latency_tester.settings import default_data_dir
    assert default_data_dir() == tmp_path / "portable"


# ------------------------------------------------------------------ i18n ----
def test_italian_and_english_are_available():
    translator = i18n.Translator("it")
    assert set(translator.available()) >= {"it", "en"}


def test_translation_switches_language():
    translator = i18n.Translator("it")
    italian = translator("live.save_run")
    translator.set_language("en")
    assert translator("live.save_run") != italian


def test_parameters_are_interpolated():
    translator = i18n.Translator("en")
    assert "42" in translator("log.saved", id=42)


def test_unknown_language_falls_back():
    translator = i18n.Translator("klingon")
    assert translator.language == i18n.FALLBACK_LANGUAGE


def test_unknown_key_returns_the_key():
    assert i18n.Translator("it")("nope.not.here") == "nope.not.here"


def test_missing_key_falls_back_to_english(monkeypatch):
    monkeypatch.setitem(i18n.TRANSLATIONS, "it", {})
    assert i18n.Translator("it")("live.save_run") == \
        i18n.TRANSLATIONS["en"]["live.save_run"]


def test_every_language_defines_the_same_keys():
    english = set(i18n.TRANSLATIONS["en"])
    for code, table in i18n.TRANSLATIONS.items():
        assert set(table) == english, f"{code} has a different key set"


def test_language_change_notifies_subscribers():
    translator = i18n.Translator("it")
    seen = []
    translator.subscribe(seen.append)
    translator.set_language("en")
    translator.set_language("en")     # no change -> no second callback
    assert seen == ["en"]


def test_protocol_tokens_are_never_translated():
    """UI strings may mention a token, but no translation may *replace* one."""
    from latency_tester import protocol
    tokens = [protocol.TOK_TRIG, protocol.TOK_ARMED, protocol.TOK_REARM,
              protocol.TOK_TESTMODE_ON, protocol.TOK_SKIP_OLED]
    for table in i18n.TRANSLATIONS.values():
        for token in tokens:
            assert token not in table, "a protocol token must not be a UI key"
