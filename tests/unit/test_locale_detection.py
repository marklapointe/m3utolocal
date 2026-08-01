from m3utolocal.i18n import LocaleService, detect_language, set_language, get_language
from m3utolocal.i18n.languages import available_languages


def test_default_en():
    assert detect_language(environ={}) == "en"


def test_lang_env():
    assert detect_language(environ={"LANG": "es_ES.UTF-8"}) == "es"


def test_config_beats_env():
    assert (
        detect_language(config_lang="de", environ={"LANG": "es_ES.UTF-8"}) == "de"
    )


def test_cli_beats_config():
    assert (
        detect_language(cli_lang="de", config_lang="es", environ={"LANG": "es"})
        == "de"
    )


def test_invalid_falls_back_en():
    assert detect_language(cli_lang="not-a-lang") == "en"


def test_english_first_in_menu():
    langs = available_languages()
    assert langs[0].code == "en"
    assert langs[0].native_name == "English"


def test_set_language():
    svc = LocaleService()
    assert svc.set_language("es") == "es"
    assert get_language() == "es"
    set_language("en")
