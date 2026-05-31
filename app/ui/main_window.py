from __future__ import annotations

import os
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QFileDialog, QProgressBar,
    QWidget, QPushButton, QSizePolicy, QSizeGrip,
)
from PyQt6.QtGui import QAction, QPainter, QColor
from PyQt6.QtCore import QEvent, Qt, QRectF, pyqtSignal

from assets.icon import make_icon

from .views import SampleView
from .dialogs import question as dlg_question, information as dlg_info, warning as dlg_warn, about as dlg_about


class _StyledSizeGrip(QSizeGrip):
    """Resize grip styled to match the app's dark theme.

    Draws a triangular pattern of six teal (#00ADB5) dots on a #2D2D2D
    background — three diagonal rows radiating from the bottom-right corner.
    """

    _BG = QColor("#2D2D2D")
    _DOT = QColor("#00ADB5")

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fill background to match the status bar
        painter.fillRect(self.rect(), self._BG)

        w = float(self.width())
        h = float(self.height())
        r   = 1.5   # dot radius in px
        gap = 4.0   # centre-to-centre spacing

        painter.setBrush(self._DOT)
        painter.setPen(Qt.PenStyle.NoPen)

        # 3 diagonal rows (1 + 2 + 3 = 6 dots) forming a right-triangle
        # pointing toward the bottom-right corner.
        #
        #  diag=2  •
        #  diag=1  • •
        #  diag=0  • • •   ← closest to corner
        #
        for diag in range(3):
            for step in range(diag + 1):
                cx = w - gap * (diag - step + 1)
                cy = h - gap * (step + 1)
                painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))


class MainWindow(QMainWindow):
    key_detected = pyqtSignal(str, object)
    startup_complete = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SampleFlow v2.0")
        self.resize(1000, 700)
        self.setWindowIcon(make_icon())

        self.view = SampleView(self)
        self.view.data_loaded.connect(self.startup_complete)
        self.setCentralWidget(self.view)

        self._scanner: Optional[ScannerThread] = None
        self._organizer: Optional[OrganizerThread] = None
        self._scan_root: Optional[str] = None
        self._key_total: int = 0
        self._key_done: int = 0
        self._deep_resolved: int = 0
        self._scan_complete: bool = False
        self._scan_total: int = 0
        self._settings_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "settings.json")
        )

        from app import translations as _tr
        _tr.set_lang(self._load_settings().get("lang", "en"))

        self._create_actions()
        self.key_detected.connect(self._on_key_detected)
        self._apply_dark_theme()
        self.retranslate_ui()

        # Replace the default status-bar grip with our styled version.
        self.statusBar().setSizeGripEnabled(False)
        self._grip = _StyledSizeGrip(self)
        self._grip.setFixedSize(16, 16)
        self.statusBar().addPermanentWidget(self._grip)

    def _create_actions(self):
        self._act_scan = QAction("", self)
        self._act_scan.triggered.connect(self.start_scan)
        self._act_stop = QAction("", self)
        self._act_stop.triggered.connect(self.stop_scan)
        self._act_choose = QAction("", self)
        self._act_choose.triggered.connect(self.choose_folder)
        self._act_cleanup = QAction("", self)
        self._act_cleanup.triggered.connect(self.cleanup_database)
        self._act_detect_key = QAction("", self)
        self._act_detect_key.triggered.connect(self.detect_key_for_selected)
        self._act_organize = QAction("", self)
        self._act_organize.triggered.connect(self.organize_samples)

        self._help_menu = self.menuBar().addMenu("")
        self._act_about = QAction("", self)
        self._act_about.triggered.connect(self._show_about)
        self._help_menu.addAction(self._act_about)

        self._toolbar = self.addToolBar("Main")
        self._toolbar.setMovable(False)
        for act in (self._act_scan, self._act_stop, self._act_choose,
                    self._act_cleanup, self._act_detect_key, self._act_organize):
            self._toolbar.addAction(act)

        # push language buttons to the right
        spacer = QWidget()
        spacer.setObjectName("toolbar_spacer")
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._toolbar.addWidget(spacer)

        self._btn_en = QPushButton("EN")
        self._btn_en.setObjectName("lang_btn")
        self._btn_en.setCheckable(True)
        self._btn_en.setFixedWidth(36)
        self._btn_en.clicked.connect(lambda: self._set_language("en"))

        self._btn_ru = QPushButton("RU")
        self._btn_ru.setObjectName("lang_btn")
        self._btn_ru.setCheckable(True)
        self._btn_ru.setFixedWidth(36)
        self._btn_ru.clicked.connect(lambda: self._set_language("ru"))

        self._toolbar.addWidget(self._btn_en)
        self._toolbar.addWidget(self._btn_ru)

        self._progress = QProgressBar(self)
        self._progress.setTextVisible(False)
        self._progress.setMinimum(0)
        self._progress.setMaximum(0)
        self._progress.setFixedHeight(6)
        self._progress.setFixedWidth(200)

        from PyQt6.QtWidgets import QLabel
        self._progress_label = QLabel("")
        self._progress_label.setObjectName("progress_label")

        self.statusBar().addPermanentWidget(self._progress)
        self.statusBar().addPermanentWidget(self._progress_label)

    def _apply_dark_theme(self):
        self.setStyleSheet("""
/* ── base ── */
QMainWindow { background: #1E1E1E; }
QMainWindow::separator { width: 0px; height: 0px; background: #1E1E1E; }
QWidget#toolbar_spacer { background: #2D2D2D; }
QAbstractScrollArea::corner { background: #1E1E1E; border: none; }

QWidget {
    background: #1E1E1E;
    color: #FFFFFF;
    font-size: 13px;
    font-family: "Segoe UI", system-ui, sans-serif;
}

/* ── menu bar ── */
QMenuBar {
    background: #2D2D2D;
    color: #CCCCCC;
    border-bottom: 1px solid #1A1A1A;
    font-size: 13px;
    padding: 1px 4px;
}
QMenuBar::item { background: transparent; padding: 4px 10px; border-radius: 4px; }
QMenuBar::item:selected { background: #383838; color: #FFFFFF; }
QMenuBar::item:pressed  { background: #1A1A1A; }

/* ── toolbar ── */
QToolBar {
    background: #2D2D2D;
    border: none;
    border-bottom: 1px solid #1A1A1A;
    padding: 4px 6px;
    spacing: 2px;
    max-height: 44px;
}
QToolButton {
    background: transparent;
    color: #FFFFFF;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 5px 14px;
}
QToolButton:hover  { background: #383838; border-color: #444444; }
QToolButton:pressed { border-color: #00ADB5; }

/* ── language toggle buttons ── */
QPushButton#lang_btn {
    background: transparent;
    color: #888888;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 4px 6px;
    font-size: 11px;
    font-weight: 700;
}
QPushButton#lang_btn:hover   { color: #FFFFFF; }
QPushButton#lang_btn:checked { color: #00ADB5; border-color: #00ADB5; }

/* ── search ── */
QLineEdit {
    background: #2D2D2D;
    color: #FFFFFF;
    border: 1px solid #3A3A3A;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: #00ADB5;
    selection-color: #1E1E1E;
}
QLineEdit:focus { border-color: #00ADB5; }

/* ── tabs ── */
QTabWidget::pane { border: none; background: #1E1E1E; }
QTabBar {
    background: transparent;
    border-bottom: 1px solid #2D2D2D;
}
QTabBar::tab {
    background: transparent;
    color: #888888;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 8px 20px;
    margin-right: 2px;
}
QTabBar::tab:selected { color: #FFFFFF; border-bottom-color: #00ADB5; }
QTabBar::tab:hover:!selected { color: #CCCCCC; }

/* ── table ── */
QTableWidget {
    background: #1E1E1E;
    alternate-background-color: #252525;
    color: #FFFFFF;
    border: none;
    gridline-color: transparent;
    selection-background-color: #1F3033;
    selection-color: #FFFFFF;
    outline: 0;
}
QTableWidget::item {
    padding: 0 8px;
    border: none;
    line-height: 28px;
}
QTableWidget::item:hover:!selected { background: #2D2D2D; }
QTableWidget::item:selected { background: #1F3033; }

QHeaderView { background: #2D2D2D; border: none; }
QHeaderView::section {
    background: #2D2D2D;
    color: #888888;
    border: none;
    border-right: 1px solid #1E1E1E;
    padding: 6px 8px;
    font-weight: 600;
    font-size: 12px;
}
QHeaderView::section:last { border-right: none; }
QHeaderView::up-arrow, QHeaderView::down-arrow { image: none; width: 0; height: 0; }

/* ── scrollbars ── */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px 0;
}
QScrollBar::handle:vertical {
    background: #3A3A3A;
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: #00ADB5; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }

QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 0 2px;
}
QScrollBar::handle:horizontal {
    background: #3A3A3A;
    border-radius: 4px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover { background: #00ADB5; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }

/* ── progress bar ── */
QProgressBar {
    background: #2D2D2D;
    border: none;
    border-radius: 3px;
    min-height: 6px;
    max-height: 6px;
}
QProgressBar::chunk { background: #00ADB5; border-radius: 3px; }

/* ── size grip (background only; dots are drawn via paintEvent) ── */
QSizeGrip {
    background: #2D2D2D;
    width: 16px;
    height: 16px;
}

/* ── status bar ── */
QStatusBar {
    background: #2D2D2D;
    color: #888888;
    font-size: 12px;
    padding: 2px 6px;
}
QStatusBar::item { border: none; }
QLabel#progress_label {
    color: #00ADB5;
    font-size: 12px;
    font-weight: 600;
    padding: 0 6px 0 6px;
}

/* ── menus ── */
QMenu {
    background: #2D2D2D;
    color: #FFFFFF;
    border: 1px solid #3A3A3A;
    padding: 4px 0;
}
QMenu::item { padding: 6px 20px; }
QMenu::item:selected { background: #383838; color: #00ADB5; }

/* ── message boxes ── */
QMessageBox { background: #2D2D2D; }
QPushButton {
    background: #2D2D2D;
    color: #FFFFFF;
    border: 1px solid #3A3A3A;
    border-radius: 6px;
    padding: 5px 16px;
    min-width: 64px;
}
QPushButton:hover  { border-color: #00ADB5; color: #00ADB5; }
QPushButton:pressed { background: #1A1A1A; }
""")

    # ------------------------------------------------------------------
    # Settings & i18n
    # ------------------------------------------------------------------
    def _load_settings(self) -> dict:
        import json
        try:
            with open(self._settings_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_settings(self, data: dict) -> None:
        import json
        try:
            existing = self._load_settings()
            existing.update(data)
            with open(self._settings_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _set_language(self, lang: str) -> None:
        from app import translations as _tr
        _tr.set_lang(lang)
        self.retranslate_ui()
        self._save_settings({"lang": lang})

    def retranslate_ui(self) -> None:
        from app import translations as _tr
        t = _tr.tr
        lang = _tr.current_lang()

        self._act_scan.setText(t("scan"))
        self._act_stop.setText(t("stop"))
        self._act_choose.setText(t("choose_folder"))
        self._act_cleanup.setText(t("clear_db"))
        self._act_detect_key.setText(t("detect_key"))
        self._act_organize.setText(t("organize"))

        self._help_menu.setTitle(t("help"))
        self._act_about.setText(t("about"))

        self._btn_en.setChecked(lang == "en")
        self._btn_ru.setChecked(lang == "ru")

        self.view.retranslate_ui(t)

    # ------------------------------------------------------------------
    def start_scan(self):
        if self._scanner and self._scanner.isRunning():
            return

        from app import translations as _tr
        t = _tr.tr
        if dlg_question(self, t("dlg_clear_db_title"),
                        t("dlg_clear_db_pre_scan"),
                        yes=t("dlg_yes"), no=t("dlg_no")):
            self.cleanup_database(show_result=False)

        from app.core.scanner import ScannerThread

        self._deep_resolved = 0
        self._scan_complete = False
        root = self._scan_root or os.path.abspath(os.path.join(__file__, "..", "..", ".."))
        self._scanner = ScannerThread(root)
        self._scanner.sample_scanned.connect(self._on_sample_scanned)
        self._scanner.progress.connect(self._on_progress)
        self._scanner.error.connect(lambda e: print("Scanner error:", e))
        self._scanner.finished.connect(self._on_scan_finished)
        self._scanner.analysis_completed.connect(self._on_bpm_analysis_done)
        self._scanner.analysis_started.connect(self._on_analysis_started)
        self._scanner.type_detected.connect(self._on_type_detected)
        self._scanner.type_analysis_started.connect(self._on_type_analysis_started)
        self._scanner.deep_progress.connect(self._on_deep_progress)
        self._scanner.scan_started.connect(self._on_scan_started)
        self._scanner.start()

        # reset progress bar until scanner emits total
        self._progress.setMaximum(0)
        self._progress.setValue(0)

    def cleanup_database(self, show_result: bool = True) -> None:
        from app.core import database
        from app import translations as _tr
        t = _tr.tr

        database.init_db()
        removed = database.delete_all_samples()
        self.view.tab_all.setRowCount(0)
        self.view.tab_dups.setRowCount(0)
        self.view.load_data()
        if show_result:
            dlg_info(self, t("dlg_clear_db_title"), t("dlg_clear_db_done").format(n=removed))

    def stop_scan(self):
        if self._scanner:
            self._scanner.stop()

    def _on_sample_scanned(self, sample: dict) -> None:
        # Add sample to UI only; database insertion is handled in the scan thread.
        self.view.add_sample(sample)

    def _pct(self) -> int:
        mx = self._progress.maximum()
        return int(self._progress.value() / mx * 100) if mx > 0 else 0

    def _on_progress(self, n: int) -> None:
        try:
            if self._progress.maximum() == 0:
                self._progress.setMaximum(1000000)
            self._progress.setValue(min(self._progress.maximum(), n))
            pct = self._pct()
            self._progress_label.setText(f"{pct}%")
            self.statusBar().showMessage(f"Scanning… {pct}%")
        except Exception:
            pass

    def choose_folder(self) -> None:
        dlg = QFileDialog(self)
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)
        if dlg.exec():
            sel = dlg.selectedFiles()
            if sel:
                self._scan_root = sel[0]

    def organize_samples(self) -> None:
        from app.core import database
        from app.core.organizer import OrganizerThread

        dlg = QFileDialog(self)
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)
        if not dlg.exec():
            return
        sel = dlg.selectedFiles()
        if not sel:
            return

        output_dir = sel[0]
        samples = database.query_samples(search=None, duplicates_only=False)
        if not samples:
            dlg_info(self, "Organize", "No samples found to organize.")
            return

        if self._organizer and self._organizer.isRunning():
            dlg_warn(self, "Organize", "Organization is already running.")
            return

        self._organizer = OrganizerThread(samples, output_dir)
        self._organizer.progress.connect(self._on_organize_progress)
        self._organizer.finished.connect(self._on_organize_finished)
        self._organizer.error.connect(lambda e: print("Organizer error:", e))
        self._organizer.start()

        self._progress.setMaximum(len(samples))
        self._progress.setValue(0)
        self._progress_label.setText("0%")
        self.statusBar().showMessage("Organizing… 0%")

    def detect_key_for_selected(self) -> None:
        from app import translations as _tr
        t = _tr.tr
        current_tab = self.view.tabs.currentWidget()
        file_path = current_tab.get_current_file_path() if current_tab else None

        if file_path:
            self._submit_key_detection(file_path)
        else:
            if dlg_question(self, t("detect_key"),
                            t("dlg_detect_key_all"),
                            yes=t("dlg_yes"), no=t("dlg_no")):
                self._detect_key_for_unknown_samples()

    def _submit_key_detection(self, file_path: str) -> None:
        from app.core import audio_dsp
        from app.core.scanner import executor

        try:
            fut = executor.submit(audio_dsp.analyze_key, file_path)

            def _cb(fut, fp=file_path, selfref=self):
                try:
                    res = fut.result()
                except Exception:
                    res = None
                selfref.key_detected.emit(fp, res)

            fut.add_done_callback(_cb)
        except Exception as e:
            print('Failed to submit key detection:', e)

    def _detect_key_for_unknown_samples(self) -> None:
        from app.core import database
        from app import translations as _tr
        t = _tr.tr

        samples = database.query_samples(search=None, duplicates_only=False)
        pending = [
            s for s in samples
            if not s["audio_key"] and s["file_path"] and os.path.exists(s["file_path"])
        ]
        if not pending:
            dlg_info(self, t("detect_key"), t("dlg_no_files_without_key"))
            return

        self._key_total = len(pending)
        self._key_done = 0
        self._progress.setMaximum(self._key_total)
        self._progress.setValue(0)
        self._progress_label.setText("0%")
        self.statusBar().showMessage(f"Detecting key for {self._key_total} files… 0%")

        for sample in pending:
            self._submit_key_detection(sample["file_path"])

    def _relocate_from_unknown(self, file_path: str, key: str) -> str:
        """If file sits in a folder named 'Unknown', move it to a sibling folder named after the key."""
        import shutil

        parent = os.path.dirname(file_path)
        if os.path.basename(parent) != "Unknown":
            return file_path

        key_dir = os.path.join(os.path.dirname(parent), key)
        os.makedirs(key_dir, exist_ok=True)

        dest = os.path.join(key_dir, os.path.basename(file_path))
        if os.path.exists(dest):
            base, ext = os.path.splitext(os.path.basename(file_path))
            counter = 1
            while os.path.exists(dest):
                dest = os.path.join(key_dir, f"{base}_{counter}{ext}")
                counter += 1

        try:
            shutil.move(file_path, dest)
            return dest
        except Exception as e:
            print(f"Relocate failed: {e}")
            return file_path

    def _on_type_detected(self, file_path: str, sample_type: str) -> None:
        try:
            from app.core import database

            stored = sample_type if sample_type and sample_type != "Other" else None
            if stored:
                self._deep_resolved += 1
            database.update_sample_type(file_path, stored)
            row = database.fetch_sample(file_path=file_path)
            if row:
                self.view.update_sample(dict(row))
        except Exception as e:
            print("Type update failed:", e)

    def _on_bpm_analysis_done(self, file_path: str, bpm: object) -> None:
        # update DB and UI when BPM analysis completes
        try:
            from app.core import database

            database.update_sample_by_path(file_path, bpm=bpm if bpm is not None else None)
            row = database.fetch_sample(file_path=file_path)
            if row:
                self.view.update_sample(dict(row))
                # clear analyzing marker
                self.view.tab_all.set_analyzing(file_path, False)
                self.view.tab_dups.set_analyzing(file_path, False)
        except Exception as e:
            print('BPM update failed:', e)

    def _on_key_detected(self, file_path: str, key: object) -> None:
        try:
            from app.core import database

            key_str = str(key).strip() if key else None
            new_path = file_path
            if key_str:
                new_path = self._relocate_from_unknown(file_path, key_str)

            database.update_sample_by_path(file_path, audio_key=key_str)
            if new_path != file_path:
                database.rename_sample_path(file_path, new_path)

            row = database.fetch_sample(file_path=new_path)
            if row:
                self.view.update_sample(dict(row))
        except Exception as e:
            print('Key update failed:', e)
        finally:
            if self._key_total > 0:
                self._key_done += 1
                self._progress.setValue(self._key_done)
                pct = self._pct()
                self._progress_label.setText(f"{pct}%")
                self.statusBar().showMessage(f"Detecting key… {pct}%")
                if self._key_done >= self._key_total:
                    self._key_total = 0
                    self._progress.setMaximum(0)
                    self._progress_label.setText("")
                    self.statusBar().showMessage("Key detection complete", 5000)

    def _on_analysis_started(self, file_path: str) -> None:
        # mark row as analyzing
        try:
            self.view.tab_all.set_analyzing(file_path, True)
            self.view.tab_dups.set_analyzing(file_path, True)
        except Exception:
            pass

    def _on_scan_started(self, total: int) -> None:
        try:
            self._scan_total = total
            self._progress.setMaximum(total)
            self._progress.setValue(0)
            self._progress_label.setText("0%")
            self.statusBar().showMessage(f"Scanning… 0%")
        except Exception:
            pass

    def _on_organize_progress(self, current: int, total: int, file_name: str) -> None:
        try:
            self._progress.setMaximum(total)
            self._progress.setValue(current)
            pct = self._pct()
            self._progress_label.setText(f"{pct}%")
            self.statusBar().showMessage(f"Organizing: {file_name} — {pct}%")
        except Exception:
            pass

    def _on_organize_finished(self, moved: int) -> None:
        try:
            self._progress.setMaximum(0)
            self._progress.setValue(0)
            self._progress_label.setText("")
            self.statusBar().showMessage("Organization complete", 5000)
            dlg_info(self, "Organize complete", f"Moved {moved} files.")
        except Exception:
            pass

    # handlers forwarded from view
    def on_files_dropped(self, paths: list) -> None:
        from app.core.scanner import ScannerThread

        if not paths:
            return
        if self._scanner and self._scanner.isRunning():
            self._scanner.stop()
            try:
                self._scanner.sample_scanned.disconnect()
                self._scanner.progress.disconnect()
                self._scanner.error.disconnect()
                self._scanner.finished.disconnect()
                self._scanner.analysis_completed.disconnect()
                self._scanner.analysis_started.disconnect()
                self._scanner.type_detected.disconnect()
                self._scanner.type_analysis_started.disconnect()
                self._scanner.deep_progress.disconnect()
                self._scanner.scan_started.disconnect()
            except Exception:
                pass
        self._deep_resolved = 0
        self._scan_complete = False
        self._scanner = ScannerThread(paths)
        self._scanner.sample_scanned.connect(self._on_sample_scanned)
        self._scanner.progress.connect(self._on_progress)
        self._scanner.error.connect(lambda e: print("Scanner error:", e))
        self._scanner.finished.connect(self._on_scan_finished)
        self._scanner.analysis_completed.connect(self._on_bpm_analysis_done)
        self._scanner.analysis_started.connect(self._on_analysis_started)
        self._scanner.type_detected.connect(self._on_type_detected)
        self._scanner.type_analysis_started.connect(self._on_type_analysis_started)
        self._scanner.deep_progress.connect(self._on_deep_progress)
        self._scanner.scan_started.connect(self._on_scan_started)
        self._scanner.start()

    def _on_scan_finished(self) -> None:
        from app import translations as _tr
        t = _tr.tr
        self._scan_complete = True
        scanner = self._scanner

        # Always show scan-complete notification first.
        self.statusBar().showMessage(
            t("status_scan_complete_n").format(n=self._scan_total), 5000
        )

        if scanner and scanner._deep_total > 0:
            # Deep analysis still running — transition progress bar to deep mode.
            total = scanner._deep_total
            done = scanner._deep_done
            self._progress.setMaximum(total)
            self._progress.setValue(done)
            pct = int(done / total * 100) if total > 0 else 0
            self._progress_label.setText(f"{pct}%")
            # If all deep tasks already finished before scan ended, finalize now.
            if done >= total:
                self._finalize_deep_analysis(total)
        else:
            self._progress.setMaximum(0)
            self._progress.setValue(0)
            self._progress_label.setText("")

    def _finalize_deep_analysis(self, total: int) -> None:
        from app import translations as _tr
        t = _tr.tr
        self._progress.setMaximum(0)
        self._progress.setValue(0)
        self._progress_label.setText("")
        resolved = self._deep_resolved
        self.statusBar().showMessage(
            t("status_scan_complete_n").format(n=self._scan_total)
            + "  |  "
            + t("status_analysis_done").format(resolved=resolved, total=total),
            8000,
        )
        self._deep_resolved = 0
        self._scan_complete = False

    def _on_type_analysis_started(self, file_path: str) -> None:
        try:
            self.view.tab_all.set_type_analyzing(file_path, True)
            self.view.tab_dups.set_type_analyzing(file_path, True)
        except Exception:
            pass

    def _on_deep_progress(self, done: int, total: int) -> None:
        try:
            from app import translations as _tr
            t = _tr.tr
            self._progress.setMaximum(total)
            self._progress.setValue(done)
            pct = int(done / total * 100) if total > 0 else 0
            self._progress_label.setText(f"{pct}%")
            self.statusBar().showMessage(
                t("status_scan_complete_n").format(n=self._scan_total)
                + "  |  "
                + t("status_type_analysis").format(done=done, total=total, pct=pct)
            )
            # Only finalize when the scan thread has also finished — otherwise
            # _deep_total is still growing and done==total is a false positive.
            if self._scan_complete and done >= total:
                self._finalize_deep_analysis(total)
        except Exception:
            pass

    def _show_about(self) -> None:
        from app import translations as _tr
        dlg_about(self, _tr.current_lang())

    def closeEvent(self, event: QEvent) -> None:
        from app.core.scanner import executor

        if self._scanner and self._scanner.isRunning():
            self._scanner.stop()
            self._scanner.wait(2000)
        if self._organizer and self._organizer.isRunning():
            self._organizer.quit()
            self._organizer.wait(2000)
        executor.shutdown(wait=False, cancel_futures=True)
        super().closeEvent(event)

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            if not self.isMinimized():
                self.activateWindow()
                self.raise_()

    def on_delete_requested(self, file_path: str) -> None:
        from app.core import database

        database.delete_sample_by_path(file_path)
        self.view.remove_sample(file_path)

    def on_reveal_requested(self, file_path: str) -> None:
        import subprocess, platform

        try:
            if platform.system() == 'Windows':
                os.startfile(os.path.normpath(file_path))
            elif platform.system() == 'Darwin':
                subprocess.run(['open', '-R', file_path])
            else:
                subprocess.run(['xdg-open', os.path.dirname(file_path)])
        except Exception as e:
            print('Reveal failed:', e)
