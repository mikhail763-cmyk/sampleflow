from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QTabWidget, QLabel
from PyQt6.QtCore import Qt, QTimer, QThread, QObject, pyqtSignal

from .widgets import SampleTable
from app.core import database


class SampleLoadWorker(QObject):
    all_rows_chunk = pyqtSignal(list)
    dups_rows_chunk = pyqtSignal(list)
    finished = pyqtSignal()

    def run(self) -> None:
        all_rows = database.query_samples(search=None, duplicates_only=False)
        dups = database.query_samples(search=None, duplicates_only=True)

        chunk_size = 200
        for i in range(0, len(all_rows), chunk_size):
            chunk = [dict(r) for r in all_rows[i : i + chunk_size]]
            self.all_rows_chunk.emit(chunk)

        for i in range(0, len(dups), chunk_size):
            chunk = [dict(r) for r in dups[i : i + chunk_size]]
            self.dups_rows_chunk.emit(chunk)

        self.finished.emit()


class SampleView(QWidget):
    data_loaded = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.layout = QVBoxLayout(self)

        self.search = QLineEdit(self)
        self.search.setPlaceholderText("Search by file name...")
        self.layout.addWidget(self.search)

        self.tabs = QTabWidget(self)
        self.tab_all = SampleTable(self)
        self.tab_dups = SampleTable(self)
        self.tabs.addTab(self.tab_all, "All")
        self.tabs.addTab(self.tab_dups, "Duplicates")
        self.layout.setContentsMargins(8, 6, 8, 8)
        self.layout.setSpacing(6)
        self.layout.addWidget(self.tabs)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._refresh)
        self.search.textChanged.connect(lambda: self._search_timer.start(250))

        self._loader_thread: QThread | None = None
        self._loader: SampleLoadWorker | None = None

        QTimer.singleShot(0, self.load_data)

        # connect drop/context signals to forward
        self.tab_all.filesDropped.connect(self._on_files_dropped)
        self.tab_all.deleteRequested.connect(self._on_delete_requested)
        self.tab_all.revealRequested.connect(self._on_reveal_requested)

        self.tab_dups.deleteRequested.connect(self._on_delete_requested)
        self.tab_dups.revealRequested.connect(self._on_reveal_requested)

    def load_data(self) -> None:
        if self._loader_thread is not None:
            return

        self.tab_all.setRowCount(0)
        self.tab_dups.setRowCount(0)

        self._loader_thread = QThread(self)
        self._loader = SampleLoadWorker()
        self._loader.moveToThread(self._loader_thread)
        self._loader.all_rows_chunk.connect(self._on_all_rows_chunk)
        self._loader.dups_rows_chunk.connect(self._on_dups_rows_chunk)
        self._loader.finished.connect(self._on_load_finished)
        self._loader_thread.started.connect(self._loader.run)
        self._loader.finished.connect(self._loader_thread.quit)
        self._loader_thread.finished.connect(self._loader.deleteLater)
        self._loader_thread.finished.connect(self._loader_thread.deleteLater)
        self._loader_thread.finished.connect(self._on_loader_thread_done)
        self._loader_thread.start()

    def _on_all_rows_chunk(self, rows: list) -> None:
        for sample in rows:
            self.tab_all.append_sample(sample)

    def _on_dups_rows_chunk(self, rows: list) -> None:
        for sample in rows:
            self.tab_dups.append_sample(sample)

    def _on_load_finished(self) -> None:
        self.data_loaded.emit()

    def _on_loader_thread_done(self) -> None:
        self._loader_thread = None

    def _refresh(self) -> None:
        txt = self.search.text().strip()
        all_rows = database.query_samples(search=txt if txt else None, duplicates_only=False)
        dups = database.query_samples(search=txt if txt else None, duplicates_only=True)

        self.tab_all.setRowCount(0)
        self.tab_dups.setRowCount(0)

        for r in all_rows:
            sample = dict(r)
            self.tab_all.add_or_update_sample(sample)

        for r in dups:
            sample = dict(r)
            self.tab_dups.add_or_update_sample(sample)

    def add_sample(self, sample: dict) -> None:
        # called when scanner emits; insert into DB already done by main
        self.tab_all.add_or_update_sample(sample)
        if sample.get("is_duplicate"):
            self.tab_dups.add_or_update_sample(sample)

    def remove_sample(self, file_path: str) -> None:
        for tbl in (self.tab_all, self.tab_dups):
            tbl.remove_by_path(file_path)

    # internal forwards
    def _on_files_dropped(self, paths: list) -> None:
        # forward to parent window to handle import/scan
        if hasattr(self.parent(), 'on_files_dropped'):
            self.parent().on_files_dropped(paths)

    def _on_delete_requested(self, file_path: str) -> None:
        if hasattr(self.parent(), 'on_delete_requested'):
            self.parent().on_delete_requested(file_path)

    def _on_reveal_requested(self, file_path: str) -> None:
        if hasattr(self.parent(), 'on_reveal_requested'):
            self.parent().on_reveal_requested(file_path)

    def update_sample(self, sample: dict) -> None:
        self.tab_all.add_or_update_sample(sample)
        if sample.get("is_duplicate"):
            self.tab_dups.add_or_update_sample(sample)

    def retranslate_ui(self, t) -> None:
        self.search.setPlaceholderText(t("search_placeholder"))
        self.tabs.setTabText(0, t("all"))
        self.tabs.setTabText(1, t("duplicates"))
        self.tab_all.retranslate_ui(t)
        self.tab_dups.retranslate_ui(t)
