from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
)
from PyQt6.QtCore import Qt

_BASE_STYLE = """
QDialog {
    background: #1E1E1E;
    font-family: "Segoe UI", system-ui, sans-serif;
}
QLabel {
    background: transparent;
    color: #FFFFFF;
    font-size: 13px;
}
QLabel#dlg_title {
    color: #00ADB5;
    font-size: 14px;
    font-weight: 700;
}
QPushButton {
    background: transparent;
    color: #00ADB5;
    border: 1px solid #00ADB5;
    border-radius: 6px;
    padding: 6px 22px;
    min-width: 72px;
    font-size: 13px;
    font-family: "Segoe UI", system-ui, sans-serif;
}
QPushButton:hover  { background: #00ADB5; color: #1E1E1E; }
QPushButton:pressed { background: #007F86; color: #1E1E1E; }
QPushButton#dlg_cancel {
    color: #666666;
    border-color: #444444;
}
QPushButton#dlg_cancel:hover {
    background: #2D2D2D;
    color: #CCCCCC;
    border-color: #777777;
}
"""

_ABOUT_EXTRA = """
QLabel#about_app {
    color: #00ADB5;
    font-size: 20px;
    font-weight: 700;
}
QLabel#about_body {
    color: #888888;
    font-size: 12px;
}
"""


class _Dlg(QDialog):
    def __init__(self, parent, title: str, text: str, buttons: list):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setStyleSheet(_BASE_STYLE)
        self.setMinimumWidth(380)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(10)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("dlg_title")
        lay.addWidget(title_lbl)

        body = QLabel(text)
        body.setWordWrap(True)
        lay.addWidget(body)
        lay.addSpacing(6)

        row = QHBoxLayout()
        row.addStretch()
        self._val = None
        for label, val, primary in buttons:
            btn = QPushButton(label)
            if not primary:
                btn.setObjectName("dlg_cancel")
            def _h(_checked=False, v=val):
                self._val = v
                self.accept()
            btn.clicked.connect(_h)
            row.addWidget(btn)
        lay.addLayout(row)

    def result_value(self):
        return self._val


class _AboutDlg(QDialog):
    def __init__(self, parent, lang: str):
        super().__init__(parent)
        self.setWindowTitle("О программе" if lang == "ru" else "About")
        self.setStyleSheet(_BASE_STYLE + _ABOUT_EXTRA)
        self.setMinimumWidth(320)
        self.setMaximumWidth(420)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 28, 32, 24)
        lay.setSpacing(6)

        app_lbl = QLabel("SampleFlow v2.0")
        app_lbl.setObjectName("about_app")
        app_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(app_lbl)

        lay.addSpacing(6)

        if lang == "ru":
            lines = [
                "Органайзер музыкальных сэмплов",
                "Разработчик и артист: mi:Enko",
                "© 2026 Все права защищены",
            ]
        else:
            lines = [
                "Music Sample Organizer",
                "Developer & Artist: mi:Enko",
                "© 2026 All rights reserved",
            ]

        body = QLabel("\n".join(lines))
        body.setObjectName("about_body")
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(body)

        lay.addSpacing(18)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.setFixedWidth(90)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)


def question(parent, title: str, text: str,
             yes: str = "Yes", no: str = "No") -> bool:
    d = _Dlg(parent, title, text, [(no, False, False), (yes, True, True)])
    d.exec()
    return d.result_value() is True


def information(parent, title: str, text: str, ok: str = "OK") -> None:
    _Dlg(parent, title, text, [(ok, True, True)]).exec()


def warning(parent, title: str, text: str, ok: str = "OK") -> None:
    _Dlg(parent, title, text, [(ok, True, True)]).exec()


def about(parent, lang: str = "en") -> None:
    _AboutDlg(parent, lang).exec()
