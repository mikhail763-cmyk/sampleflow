from __future__ import annotations

import os
import re
import shutil
from typing import Callable, Iterable, Optional

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

try:
    import librosa
except Exception:  # pragma: no cover - librosa expected in requirements
    librosa = None

from app.core.scanner import executor
from app.core import database

TYPE_KEYWORDS = [
    # 1. Vocal — highest priority
    ("Vocal",     [r"\bvocal\b", r"\bvox\b", r"\bvoice\b", r"\bchop\b", r"\bacapella\b",
                   r"\badlib\b", r"\bharmony\b", r"\bchoir\b", r"\btopline\b", r"\bformant\b"]),
    # 2. FX (foley merged in)
    ("FX",        [r"\briser\b", r"\bsweep\b", r"\bdownlifter\b", r"\buplifter\b", r"\bimpact\b",
                   r"\bwhoosh\b", r"\btransition\b", r"\bglitch\b", r"\breverse\b", r"\bnoise\b",
                   r"\bzap\b", r"\bfoley\b", r"\bfx\b", r"\beffect\b"]),
    # 3. Kick before Bass — "bass_kick.wav" → Kick, not Bass
    ("Kick",      [r"\bkick\b", r"\bbd\b", r"\bbass[\s_]drum\b", r"\bbump\b"]),
    # 4. Melodic/harmonic types
    ("Bass",      [r"\bbass\b", r"\bbassline\b", r"\bsub\b", r"\b808\b"]),
    ("Lead",      [r"\blead\b", r"\bsynth\b", r"\bmono\b"]),
    ("Melodic",   [r"\bguitar\b", r"\bpiano\b", r"\bgrand\b", r"\bkeys?\d*\b",
                   r"\bstrings\b", r"\bviolin\b", r"\bflute\b", r"\bshakuhachi\b",
                   r"\bbrass\b", r"\bhorn\b", r"\bsax\b", r"\borgan\b", r"\bharp\b",
                   r"\bbell\b", r"\bensemble\b", r"\barp\b", r"\bmelod(y|ic)\b",
                   r"\briff\b", r"\bhook\b", r"\bchord\b", r"\bstab\b", r"\bpluck\b",
                   r"\bpad\b", r"\brhodes\b", r"\bwurlitzer\b", r"\bmarimba\b",
                   r"\bvibraphone\b", r"\bxylophone\b", r"\bglockenspiel\b",
                   r"\bsitar\b", r"\boud\b", r"\bivory\b", r"\bmallet\b", r"\bnylon\b",
                   r"\bkit\b", r"\blog\s+drum\b"]),
    # 5. Drum Loop before remaining drum one-shots
    ("Drum Loop", [r"\bdrum[\s_]?loop\b", r"\bdrums[\s_]?\w*[\s_]?loop\b",
                   r"\bdrum[\s_]top[\s_]loop\b", r"\bdrumloop\b",
                   r"\bgroove\b", r"\bbreak\b", r"\bbreakbeat\b"]),
    # 6. Remaining drum one-shots
    ("Snare",     [r"\bsnare\b", r"\bsd\b", r"\bclap\b", r"\bsnap\b", r"\brimshot\b", r"\brim\b"]),
    ("Hi-Hat",    [r"\bhihat\b", r"\bhi-hat\b", r"\bhat\b", r"\bhh\b",
                   r"\bopen[\s_]hat\b", r"\bclosed[\s_]hat\b", r"\bdrum[\s_]top\b"]),
    ("Cymbal",    [r"\bcymbal\b", r"\bcrash\b", r"\bride\b", r"\bsplash\b"]),
    # Perc: \bperc\w*\b catches perc/percs/percussion/percloop/perconeshot etc.
    # otherperc needs explicit pattern — "perc" is mid-word there, no leading \b
    ("Perc",      [r"\bperc\w*\b", r"\bshaker\b", r"\btambourine\b",
                   r"\bconga\b", r"\bcongaloop\b", r"\bbongo\b", r"\btom\b",
                   r"\btabla\b", r"\bdarbuka\b", r"\bdarbouka\b", r"\bdjembe\b",
                   r"\bcowbell\b", r"\btriangle\b", r"\bfill\b", r"\bdrums\b",
                   r"\bmetal\s*loop\b", r"\botherperc\b"]),
    # 7. Last-resort catches — checked after ALL drum one-shots so specific types win.
    # "beat" standalone (e.g. BEAT_01_B_126) → Drum Loop; snare/hat/perc still override.
    ("Drum Loop", [r"\bbeat\b"]),
    # "afrobeat" compound word has no boundary before "beat" so \bbeat\b misses it.
    ("Melodic",   [r"\bafrobeat\b"]),
]

# Types that get full hierarchy: Category/Subtype/Key
# Note: "Pad" and "Chord" are intentionally absent — keywords "pad"/"chord"
# in filenames match the "Melodic" entry in TYPE_KEYWORDS and land in
# Melodic/Melodic/<key>, which is correct.
HIERARCHICAL_TYPES: dict[str, tuple[str, str]] = {
    "Kick":        ("Drums",   "Kick"),
    "Snare":       ("Drums",   "Snare"),
    "Hi-Hat":      ("Drums",   "Hi-Hat"),
    "Cymbal":      ("Drums",   "Cymbal"),
    "Perc":        ("Drums",   "Perc"),
    "Drum Loop":   ("Drums",   "Drum Loop"),
    "Bass":        ("Melodic", "Bass"),
    "Lead":        ("Melodic", "Lead"),
    "Melody Loop": ("Melodic", "Melody Loop"),
    "Melodic":     ("Melodic", "Melodic"),
}

# Types placed in a flat folder with no BPM/key subfolders
FLAT_TYPES: set[str] = {"FX", "Other"}


def _match_keyword(name: str) -> Optional[str]:
    stem = os.path.splitext(name)[0]
    # Strip leading key prefixes like A_minor_, Bb_major_, Fmaj_, etc.
    stem = re.sub(r'^[A-Ga-g][#b]?[\s_]*(major|minor|maj|min)[\s_]+', '', stem, flags=re.IGNORECASE)
    # Normalize underscores to spaces so \b word boundaries work correctly
    stem = stem.replace('_', ' ')
    for sample_type, patterns in TYPE_KEYWORDS:
        for pattern in patterns:
            if re.search(pattern, stem, re.IGNORECASE):
                return sample_type
    return None


def _audio_type_from_signal(y: np.ndarray, sr: int) -> str:
    duration = len(y) / sr if sr else 0.0
    n_fft = max(32, min(512, len(y)))
    hop_length = max(1, n_fft // 4)

    try:
        centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr, n_fft=n_fft, hop_length=hop_length))
    except Exception:
        centroid = None

    if duration < 0.25:
        return "Perc"

    if duration < 1.0:
        if centroid is not None and centroid < 1200:
            return "Kick"
        return "Snare"

    if duration >= 2.0:
        # --- onset regularity: regular → Drum Loop ---
        is_drum_loop = False
        try:
            onset_env = librosa.onset.onset_strength(y=y, sr=sr, n_fft=n_fft, hop_length=hop_length)
            onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, hop_length=hop_length)
            times = librosa.frames_to_time(onsets, sr=sr, hop_length=hop_length)
            if len(times) >= 4:
                diffs = np.diff(times)
                if len(diffs) > 0 and np.std(diffs) < 0.15:
                    is_drum_loop = True
        except Exception:
            pass

        if is_drum_loop:
            return "Drum Loop"

        # --- harmonic content: chroma present → Melody Loop ---
        has_pitch = False
        try:
            chroma = librosa.feature.chroma_stft(y=y, sr=sr, n_fft=n_fft, hop_length=hop_length)
            if np.mean(chroma) > 0.01:
                has_pitch = True
        except Exception:
            pass

        if has_pitch:
            return "Melody Loop"

        # --- irregular onsets + no pitch + high centroid → FX (riser, sweep, noise) ---
        # At sr=11025 the full range is 0–5512 Hz; centroid > 3000 Hz means
        # energy is weighted toward the top half — typical of noise-based FX.
        if centroid is not None and centroid > 3000:
            return "FX"

    return "Other"


def detect_type(file_path: str, y: Optional[np.ndarray] = None, sr: Optional[int] = None) -> str:
    name = os.path.basename(file_path)
    sample_type = _match_keyword(name)
    if sample_type:
        return sample_type

    if y is None or sr is None or librosa is None:
        return "Other"

    return _audio_type_from_signal(y, sr)


def _load_audio_for_type(file_path: str) -> tuple[Optional[np.ndarray], Optional[int]]:
    if librosa is None:
        return None, None
    try:
        y, sr = librosa.load(file_path, sr=11025, duration=15)
        return y, sr
    except Exception:
        return None, None


def _make_unique_path(path: str) -> str:
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    counter = 1
    while True:
        candidate = f"{base}_{counter}{ext}"
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def organize_files(samples: Iterable[dict], output_dir: str, progress_callback: Optional[Callable[[int, int, str], None]] = None) -> int:
    samples = list(samples)
    total = len(samples)
    moved = 0

    abs_output = os.path.abspath(output_dir)

    for index, sample in enumerate(samples, start=1):
        file_path = sample.get("file_path") if isinstance(sample, dict) else sample["file_path"]
        if not file_path or not os.path.exists(file_path):
            continue

        # Skip files that are already inside output_dir — they were organized previously.
        # Use normcase for case-insensitive comparison on Windows.
        if os.path.normcase(os.path.abspath(file_path)).startswith(
            os.path.normcase(abs_output + os.sep)
        ):
            continue

        # Prefer the type stored in the database (may have been manually corrected).
        try:
            sample_type = (
                sample.get("sample_type") if isinstance(sample, dict)
                else sample["sample_type"]
            ) or None
        except (KeyError, IndexError):
            sample_type = None

        if not sample_type:
            sample_type = detect_type(file_path)

        if sample_type == "Other" or not sample_type:
            y, sr = None, None
            future = executor.submit(_load_audio_for_type, file_path)
            try:
                y, sr = future.result()
            except Exception:
                y, sr = None, None
            if y is not None and sr is not None:
                sample_type = detect_type(file_path, y=y, sr=sr)

        if not sample_type:
            sample_type = "Other"

        audio_key = sample.get("audio_key") if isinstance(sample, dict) else sample["audio_key"]

        if sample_type in HIERARCHICAL_TYPES:
            top_cat, subtype = HIERARCHICAL_TYPES[sample_type]
            key_folder = str(audio_key).strip() if audio_key else "Unknown"
            dest_dir = os.path.join(output_dir, top_cat, subtype, key_folder)
        elif sample_type == "Vocal":
            key_folder = str(audio_key).strip() if audio_key else "Unknown"
            dest_dir = os.path.join(output_dir, "Vocal", key_folder)
        else:
            dest_dir = os.path.join(output_dir, sample_type if sample_type in FLAT_TYPES else "Other")
        os.makedirs(dest_dir, exist_ok=True)

        new_name = os.path.basename(file_path)
        dest_path = _make_unique_path(os.path.join(dest_dir, new_name))

        try:
            shutil.move(file_path, dest_path)
            moved += 1
            database.rename_sample_path(file_path, dest_path)
        except Exception:
            continue

        if progress_callback:
            progress_callback(index, total, os.path.basename(file_path))

    return moved


class OrganizerThread(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, samples: Iterable[dict], output_dir: str):
        super().__init__()
        self.samples = list(samples)
        self.output_dir = output_dir

    def run(self) -> None:
        try:
            moved = organize_files(self.samples, self.output_dir, self._on_progress)
            self.finished.emit(moved)
        except Exception as exc:
            self.error.emit(str(exc))
            self.finished.emit(0)

    def _on_progress(self, current: int, total: int, file_name: str) -> None:
        self.progress.emit(current, total, file_name)
