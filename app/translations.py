from __future__ import annotations

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "scan": "Scan",
        "stop": "Stop",
        "choose_folder": "Choose Folder",
        "clear_db": "Clear DB",
        "detect_key": "Detect Key",
        "organize": "Organize",
        "search_placeholder": "Search by file name...",
        "all": "All",
        "duplicates": "Duplicates",
        "file_name": "File Name",
        "bpm": "BPM",
        "key": "Key",
        "type": "Type",
        "size": "Size",
        "duplicate": "Duplicate",
        "help": "Help",
        "about": "About",
    },
    "ru": {
        "scan": "Сканировать",
        "stop": "Стоп",
        "choose_folder": "Выбрать папку",
        "clear_db": "Очистить базу",
        "detect_key": "Найти тональность",
        "organize": "Организовать",
        "search_placeholder": "Поиск по имени файла...",
        "all": "Все",
        "duplicates": "Дубликаты",
        "file_name": "Имя файла",
        "bpm": "BPM",
        "key": "Тональность",
        "type": "Тип",
        "size": "Размер",
        "duplicate": "Дубликат",
        "help": "Справка",
        "about": "О программе",
    },
}

_current_lang: str = "en"


def set_lang(lang: str) -> None:
    global _current_lang
    if lang in TRANSLATIONS:
        _current_lang = lang


def current_lang() -> str:
    return _current_lang


def tr(key: str) -> str:
    return TRANSLATIONS.get(_current_lang, TRANSLATIONS["en"]).get(key, key)
