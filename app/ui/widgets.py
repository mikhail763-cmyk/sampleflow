from __future__ import annotations

import typing
from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QMenu, QHeaderView,
    QStyledItemDelegate, QStyle, QComboBox,
)
from PyQt6.QtGui import QDrag, QAction, QPen, QColor
from PyQt6.QtCore import Qt, QUrl, QMimeData, QPoint, pyqtSignal

_ACCENT = QColor("#00ADB5")

_TYPE_CHOICES = [
    "Kick", "Snare", "Hi-Hat", "Cymbal", "Perc", "Drum Loop",
    "Bass", "Lead", "Pad", "Melodic", "Vocal", "FX", "Other",
]


class _RowAccentDelegate(QStyledItemDelegate):
    """Draws a 3 px left accent line on the first column of selected rows."""

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        if (option.state & QStyle.StateFlag.State_Selected) and index.column() == 0:
            painter.save()
            pen = QPen(_ACCENT, 3, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            r = option.rect
            painter.drawLine(r.left() + 1, r.top(), r.left() + 1, r.bottom())
            painter.restore()


class _TypeDelegate(QStyledItemDelegate):
    """QComboBox editor for the Type column."""

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.addItems([""] + _TYPE_CHOICES)
        return combo

    def setEditorData(self, editor, index):
        val = index.data(Qt.ItemDataRole.DisplayRole) or ""
        idx = editor.findText(val)
        editor.setCurrentIndex(max(idx, 0))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class SampleTable(QTableWidget):
    """Table widget for displaying sample rows.

    Columns: File Name, BPM, Key, Size, Duplicate
    """

    fileActivated = pyqtSignal(str)
    filesDropped = pyqtSignal(list)
    deleteRequested = pyqtSignal(str)
    revealRequested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(0, 6, parent)
        self._path_to_row: dict[str, int] = {}
        self._suppress_cell_changed = False
        self.setHorizontalHeaderLabels(["File Name", "BPM", "Key", "Type", "Size", "Duplicate"])
        self.setSelectionBehavior(self.SelectionBehavior.SelectRows)
        self.setSelectionMode(self.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setSortingEnabled(False)

        hdr = self.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(1, 70)
        self.setColumnWidth(2, 110)
        self.setColumnWidth(3, 90)   # Type
        self.setColumnWidth(4, 80)   # Size
        self.setColumnWidth(5, 76)   # Duplicate

        self._fixed_cols_width = 70 + 110 + 90 + 80 + 76

        vhdr = self.verticalHeader()
        vhdr.setVisible(False)
        vhdr.setDefaultSectionSize(28)

        self.setItemDelegate(_RowAccentDelegate(self))
        self.setItemDelegateForColumn(3, _TypeDelegate(self))

        self._drag_start_pos: QPoint | None = None
        self.setAcceptDrops(True)

        self.cellChanged.connect(self._on_cell_changed)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        vp = self.viewport().width()
        min_col0 = vp // 2
        col0 = max(vp - self._fixed_cols_width, min_col0)
        self.setColumnWidth(0, col0)

    # ------------------------------------------------------------------
    # i18n
    # ------------------------------------------------------------------
    def retranslate_ui(self, t) -> None:
        self.setHorizontalHeaderLabels(
            [t("file_name"), t("bpm"), t("key"), t("type"), t("size"), t("duplicate")]
        )

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------
    def setRowCount(self, rows: int) -> None:
        if rows == 0:
            self._path_to_row.clear()
        super().setRowCount(rows)

    def add_or_update_sample(self, sample: dict) -> None:
        file_path = sample.get("file_path")
        row = self._path_to_row.get(file_path) if file_path else None
        if row is None:
            row = self.rowCount()
            self.insertRow(row)
        self._fill_row(row, sample)

    def remove_by_path(self, file_path: str) -> None:
        row = self._path_to_row.pop(file_path, None)
        if row is None:
            return
        self.removeRow(row)
        # Shift down all row indices above the removed row.
        for path, r in self._path_to_row.items():
            if r > row:
                self._path_to_row[path] = r - 1

    def append_sample(self, sample: dict) -> None:
        row = self.rowCount()
        self.insertRow(row)
        self._fill_row(row, sample)

    def _fill_row(self, row: int, sample: dict) -> None:
        file_path = sample.get("file_path")
        if file_path:
            self._path_to_row[file_path] = row

        self._suppress_cell_changed = True
        try:
            file_name = sample.get("file_name", "")
            name_item = QTableWidgetItem(file_name)
            name_item.setData(Qt.ItemDataRole.UserRole, file_path)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name_item.setToolTip(file_name)

            bpm_item = QTableWidgetItem(str(sample.get("bpm") or ""))
            bpm_item.setFlags(bpm_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            bpm_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

            key_item = QTableWidgetItem(str(sample.get("audio_key") or ""))
            key_item.setFlags(key_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            key_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

            type_item = QTableWidgetItem(str(sample.get("sample_type") or ""))
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

            size_val = sample.get("file_size")
            size_item = QTableWidgetItem(self._format_size(size_val) if size_val is not None else "")
            size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

            dup_item = QTableWidgetItem("✓" if sample.get("is_duplicate") else "")
            dup_item.setFlags(dup_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            dup_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            if sample.get("is_duplicate"):
                dup_item.setForeground(QColor("#00ADB5"))

            self.setItem(row, 0, name_item)
            self.setItem(row, 1, bpm_item)
            self.setItem(row, 2, key_item)
            self.setItem(row, 3, type_item)
            self.setItem(row, 4, size_item)
            self.setItem(row, 5, dup_item)
        finally:
            self._suppress_cell_changed = False

    def set_analyzing(self, file_path: str, analyzing: bool) -> None:
        r = self._path_to_row.get(file_path)
        if r is None:
            return
        bpm_item = self.item(r, 1)
        if bpm_item is None:
            bpm_item = QTableWidgetItem("")
            self.setItem(r, 1, bpm_item)
        bpm_item.setText("…" if analyzing else "")

    def set_type_analyzing(self, file_path: str, analyzing: bool) -> None:
        r = self._path_to_row.get(file_path)
        if r is None:
            return
        self._suppress_cell_changed = True
        try:
            type_item = self.item(r, 3)
            if type_item is None:
                type_item = QTableWidgetItem("")
                self.setItem(r, 3, type_item)
            if analyzing and not type_item.text():
                type_item.setText("…")
            elif not analyzing and type_item.text() == "…":
                type_item.setText("")
        finally:
            self._suppress_cell_changed = False

    def _on_cell_changed(self, row: int, col: int) -> None:
        if self._suppress_cell_changed or col != 3:
            return
        file_item = self.item(row, 0)
        type_item = self.item(row, col)
        if not file_item or not type_item:
            return
        file_path = file_item.data(Qt.ItemDataRole.UserRole)
        new_type = type_item.text().strip() or None
        if file_path:
            from app.core import database
            database.update_sample_type(file_path, new_type)

    def get_current_file_path(self) -> typing.Optional[str]:
        sel = self.selectedItems()
        if not sel:
            return None
        return sel[0].data(Qt.ItemDataRole.UserRole)

    # ------------------------------------------------------------------
    # Drag & drop
    # ------------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return super().mouseMoveEvent(event)
        if self._drag_start_pos is None:
            return super().mouseMoveEvent(event)
        if (event.pos() - self._drag_start_pos).manhattanLength() < 4:
            return super().mouseMoveEvent(event)

        file_path = self.get_current_file_path()
        if not file_path:
            return super().mouseMoveEvent(event)

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(file_path)])
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.CopyAction)
        self._drag_start_pos = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
        if paths:
            self.filesDropped.emit(paths)
            event.acceptProposedAction()

    def contextMenuEvent(self, event):
        idx = self.indexAt(event.pos())
        if not idx.isValid():
            return
        item = self.item(idx.row(), 0)
        file_path = item.data(Qt.ItemDataRole.UserRole) if item else None

        menu = QMenu(self)
        act_show = QAction("Show in Explorer", self)
        act_delete = QAction("Delete from DB", self)
        menu.addAction(act_show)
        menu.addAction(act_delete)
        act_show.triggered.connect(lambda: file_path and self.revealRequested.emit(file_path))
        act_delete.triggered.connect(lambda: file_path and self.deleteRequested.emit(file_path))
        menu.exec(event.globalPos())

    def _format_size(self, size_bytes: int) -> str:
        try:
            size = int(size_bytes)
        except Exception:
            return str(size_bytes)
        if size < 1024 * 1024:
            kb = size / 1024
            return f"{kb:.0f} KB" if kb >= 10 else f"{kb:.1f} KB"
        mb = size / (1024 * 1024)
        return f"{mb:.1f} MB"
