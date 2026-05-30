"""Background filesystem scanner for audio samples.

Runs on a QThread and communicates with the UI only via pyqtSignal.
Emits a dictionary per discovered sample with the fields required by the
database schema.

The fast file hash algorithm follows the exact specification required by
the project and never reads an entire large file into memory.
"""
from __future__ import annotations

import os
import hashlib
import time
import ctypes
import platform
import concurrent.futures
from typing import Iterable

from PyQt6.QtCore import QThread, pyqtSignal

from . import audio_dsp, database

# Single-worker executor for all heavier analysis tasks to limit CPU/RAM
executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)


AUDIO_EXTS = {".wav", ".mp3", ".aiff", ".flac"}
MIN_FILE_SIZE = 10240  # 10KB


def _analyze_type_deep(file_path: str) -> str:
    """Load 3 × 2-second probes (start / middle / end), skip silent segments
    (RMS < 0.01), and return the type from the first non-silent probe.

    Lazy-imported to avoid the circular dependency with organizer.py.
    Prints progress so issues are visible in the console.
    """
    print(f"[deep] Запущен: {file_path}")
    try:
        return _analyze_type_deep_impl(file_path)
    except Exception as exc:
        import traceback
        print(f"[deep] Ошибка: {file_path}: {exc}")
        traceback.print_exc()
        return "Other"


def _analyze_type_deep_impl(file_path: str) -> str:
    try:
        import librosa
        import numpy as np
    except ImportError:
        print("[deep] librosa не установлен — пропускаем")
        return "Other"

    from app.core.organizer import _audio_type_from_signal

    # Get total duration — API differs between librosa versions.
    try:
        total = librosa.get_duration(path=file_path)
    except TypeError:
        total = librosa.get_duration(filename=file_path)

    if total <= 0:
        print(f"[deep] Нулевая длительность: {file_path}")
        return "Other"

    # Three probe offsets: start, middle, near end.
    offsets = [0.0, max(0.0, total / 2 - 1.0), max(0.0, total - 2.0)]
    unique: list[float] = []
    for off in offsets:
        if not any(abs(off - u) < 0.5 for u in unique):
            unique.append(off)

    for offset in unique:
        try:
            y, sr = librosa.load(file_path, sr=11025, offset=offset, duration=2.0, mono=True)
        except Exception as exc:
            print(f"[deep] load ошибка offset={offset:.1f}s: {exc}")
            continue

        if len(y) == 0:
            continue
        rms = float(np.sqrt(np.mean(y ** 2)))
        if rms < 0.01:
            print(f"[deep] Тихий сегмент offset={offset:.1f}s rms={rms:.4f} — пропускаем")
            continue

        result = _audio_type_from_signal(y, sr)
        print(f"[deep] offset={offset:.1f}s → {result}")
        if result != "Other":
            return result

    print(f"[deep] Результат: Other (не определено)")
    return "Other"


def get_fast_file_hash(file_path: str) -> str:
    import os, hashlib

    file_size = os.path.getsize(file_path)
    if file_size < 1024 * 1024:
        with open(file_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    with open(file_path, "rb") as f:
        first_chunk = f.read(512 * 1024)
        f.seek(-512 * 1024, os.SEEK_END)
        last_chunk = f.read(512 * 1024)
    combined = f"{file_size}".encode() + first_chunk + last_chunk
    return hashlib.md5(combined).hexdigest()


def _is_audio_file(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in AUDIO_EXTS


class ScannerThread(QThread):
    """QThread that scans given paths for audio files.

    Signals:
        sample_scanned(dict): emitted for each discovered audio file. Dict contains
            `file_path`, `file_name`, `file_size`, `file_hash`, `bpm`, `audio_key`, `is_duplicate`.
        progress(int): number of files scanned so far.
        finished(): emitted when scan completes or is stopped.
        error(str): emitted when an error occurs.
    """

    sample_scanned = pyqtSignal(object)
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    analysis_started = pyqtSignal(str)
    analysis_completed = pyqtSignal(str, object)
    type_detected = pyqtSignal(str, str)
    type_analysis_started = pyqtSignal(str)
    deep_progress = pyqtSignal(int, int)
    scan_started = pyqtSignal(int)

    def __init__(self, roots: Iterable[str] | str):
        super().__init__()
        if isinstance(roots, str):
            roots = [roots]
        self.roots = list(roots)
        self._running = True
        self._deep_total = 0
        self._deep_done = 0

    def stop(self) -> None:
        """Request the thread to stop scanning as soon as possible."""
        self._running = False

    def _lower_priority(self) -> None:
        try:
            if platform.system() == 'Windows':
                # BELOW_NORMAL_PRIORITY_CLASS
                BELOW_NORMAL = 0x00004000
                kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
                kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), BELOW_NORMAL)
            else:
                # increase niceness
                try:
                    os.nice(10)
                except Exception:
                    pass
        except Exception:
            pass

    def run(self) -> None:
        scanned = 0
        try:
            # lower process priority so scanning doesn't interfere with audio apps
            self._lower_priority()

            # Ensure database exists before inserting rows from the scan thread
            database.init_db()
            database.delete_missing_files()
            database.delete_samples_smaller_than(MIN_FILE_SIZE)

            # Gather full list of files first (so we can report total)
            files = []
            for root in self.roots:
                if not self._running:
                    break
                if os.path.isfile(root):
                    if _is_audio_file(root) and os.path.getsize(root) >= MIN_FILE_SIZE:
                        files.append(root)
                else:
                    for dirpath, _, filenames in os.walk(root, followlinks=True):
                        if not self._running:
                            break
                        for fn in filenames:
                            full = os.path.join(dirpath, fn)
                            if not _is_audio_file(full):
                                continue
                            try:
                                if os.path.getsize(full) >= MIN_FILE_SIZE:
                                    files.append(full)
                            except OSError:
                                pass
                        if not self._running:
                            break

            total = len(files)
            print(f"Найдено файлов: {total}")
            self.scan_started.emit(total)

            # process in batches of 10
            batch = []
            for idx, fpath in enumerate(files):
                if not self._running:
                    break
                batch.append(fpath)
                if len(batch) >= 10:
                    self._process_batch(batch)
                    scanned += len(batch)
                    # emit progressive counts
                    self.progress.emit(scanned)
                    batch = []
                    if not self._running:
                        break
                    time.sleep(0.05)
            if batch and self._running:
                self._process_batch(batch)
                scanned += len(batch)
                self.progress.emit(scanned)
            self.finished.emit()
        except Exception as exc:
            self.error.emit(str(exc))
            self.finished.emit()

    def _process_batch(self, paths: list[str]) -> None:
        for p in paths:
            if not self._running:
                break
            try:
                self._process_single(p)
            except Exception as e:
                self.error.emit(str(e))
            time.sleep(0.01)

    def _process_single(self, file_path: str) -> None:
        # Lazy import avoids the circular dependency with organizer.py
        from app.core.organizer import detect_type

        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            return
        file_name = os.path.basename(abs_path)
        try:
            file_size = os.path.getsize(abs_path)
        except OSError:
            return

        # Skip auxiliary/empty files smaller than 10KB
        if file_size < 10240:
            return

        file_hash = get_fast_file_hash(abs_path)

        # Parse BPM and key from filename first (cheap, no I/O).
        try:
            bpm, key = audio_dsp.parse_filename(abs_path)
        except Exception:
            bpm, key = None, None

        # Detect type from filename keywords.
        sample_type: str | None = detect_type(abs_path)
        if sample_type == "Other":
            sample_type = None  # store None until deep analysis resolves it

        # Schedule BPM analysis if not parsed from filename.
        if bpm is None:
            try:
                self.analysis_started.emit(abs_path)
                future_bpm = executor.submit(audio_dsp.analyze_bpm, abs_path)

                def _bpm_cb(fut, fp=abs_path, selfref=self):
                    try:
                        res = fut.result()
                    except Exception:
                        res = None
                    selfref.analysis_completed.emit(fp, res)

                future_bpm.add_done_callback(_bpm_cb)
            except Exception:
                pass

        # Schedule deep type analysis when keyword matching returned nothing.
        if sample_type is None:
            try:
                self._deep_total += 1
                self.type_analysis_started.emit(abs_path)
                future_type = executor.submit(_analyze_type_deep, abs_path)

                def _type_cb(fut, fp=abs_path, selfref=self):
                    selfref._deep_done += 1
                    try:
                        res = fut.result()
                    except Exception:
                        res = "Other"
                    selfref.type_detected.emit(fp, res if res else "Other")
                    selfref.deep_progress.emit(selfref._deep_done, selfref._deep_total)

                future_type.add_done_callback(_type_cb)
            except Exception:
                self._deep_total -= 1

        sample = {
            "file_path": abs_path,
            "file_name": file_name,
            "file_size": file_size,
            "file_hash": file_hash,
            "bpm": bpm,
            "audio_key": key,
            "is_duplicate": False,
            "sample_type": sample_type,
        }

        # Insert into database on the scan thread.
        try:
            database.insert_sample(
                file_path=sample["file_path"],
                file_name=sample["file_name"],
                file_size=sample["file_size"],
                file_hash=sample["file_hash"],
                bpm=sample.get("bpm"),
                audio_key=sample.get("audio_key"),
                is_duplicate=1 if sample.get("is_duplicate") else 0,
                sample_type=sample.get("sample_type"),
            )
        except Exception:
            pass

        self.sample_scanned.emit(sample)
