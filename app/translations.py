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
        # dialogs
        "dlg_clear_db_title": "Clear DB",
        "dlg_clear_db_pre_scan": "Delete records smaller than 10 240 bytes from the database before scanning?",
        "dlg_clear_db_done": "Removed {n} rows from the samples table.",
        "dlg_yes": "Yes",
        "dlg_no": "No",
        "dlg_detect_key_all": "Analyze all files without a key (Unknown)?",
        "dlg_no_files_without_key": "No files without a key.",
        # status bar
        "status_type_analysis": "Analyzing types: {done}/{total} unnamed… {pct}%",
        "status_scan_complete": "Scan complete",
        "status_scan_complete_n": "✓ Scan complete — {n} files found",
        "status_analysis_done": "✓ Type analysis: {resolved}/{total} unnamed files identified",
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
        # dialogs
        "dlg_clear_db_title": "Очистка базы",
        "dlg_clear_db_pre_scan": "Удалить записи размером меньше 10 240 байт из базы перед сканированием?",
        "dlg_clear_db_done": "Удалено {n} строк из таблицы samples.",
        "dlg_yes": "Да",
        "dlg_no": "Нет",
        "dlg_detect_key_all": "Проанализировать все файлы без тональности (Unknown)?",
        "dlg_no_files_without_key": "Нет файлов без тональности.",
        # status bar
        "status_type_analysis": "Анализ типов: {done}/{total} безымянных… {pct}%",
        "status_scan_complete": "Сканирование завершено",
        "status_scan_complete_n": "✓ Сканирование завершено — найдено {n} файлов",
        "status_analysis_done": "✓ Анализ типов: {resolved}/{total} безымянных определено",
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
