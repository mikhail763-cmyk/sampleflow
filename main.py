from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
from PyQt6.QtCore import Qt, QRect

from assets.icon import make_icon


def create_splash_screen() -> QSplashScreen:
    pixmap = QPixmap(400, 200)
    pixmap.fill(QColor("#1E1E1E"))

    painter = QPainter(pixmap)
    painter.setPen(QColor("#00ADB5"))
    painter.setFont(QFont("Arial", 24, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "SampleFlow v2.0")

    painter.setPen(QColor("#888888"))
    painter.setFont(QFont("Arial", 12))
    painter.drawText(QRect(0, 120, 400, 50), Qt.AlignmentFlag.AlignCenter, "Загрузка...")
    painter.end()

    splash = QSplashScreen(pixmap)
    return splash


def main() -> int:
    app = QApplication(sys.argv)
    app.setWindowIcon(make_icon())
    splash = create_splash_screen()
    splash.show()
    app.processEvents()

    from app.core import database
    database.init_db()
    database.delete_samples_smaller_than(10240)

    from app.ui.main_window import MainWindow
    win = MainWindow()
    win.startup_complete.connect(lambda: splash.finish(win))
    win.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
