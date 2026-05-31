"""Audio DSP helpers: BPM and key detection for SampleFlow.

Behavior:
- First try to parse BPM and key from the filename using regular expressions.
- If BPM or key not found, load only the first 15 seconds of audio with
  `librosa.load(..., duration=15, sr=11025)` and compute estimates.

Constraints honored: never read the entire file for hashing or analysis;
librosa is used strictly with `duration=15` and `sr=11025`.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

import numpy as np

# Regex patterns
# BPM: matches _120_, _120., 120BPM, (120 BPM), (120BPM), 120bpm - realistic range 80-200 only
BPM_RE = re.compile(
    r"(?:_(?:([89]\d|1\d\d|200))(?=_|\.|$|[^0-9])"
    r"|\(\s*([89]\d|1\d\d|200)(?:\s*BPM)?\s*\)"
    r"|([89]\d|1\d\d|200)\s*BPM)",
    re.IGNORECASE,
)

# Full key with explicit mode suffix — searched first (highest priority)
# Matches: Am, Fmaj, Bbmin, F#m, Ebmaj, etc.
KEY_FULL_RE = re.compile(
    r"(?:^|_)([A-G](?:#|b)?(?:min|maj|m))(?=\.wav|_|$)",
    re.IGNORECASE,
)
# Note + underscore + mode — second priority
# Matches: F_m, A_minor, D_min, C_major, Bb_maj, etc.
KEY_SPLIT_RE = re.compile(
    r"(?:^|_)([A-G](?:#|b)?)_(minor|major|min|maj|m)(?=\.wav|_|$)",
    re.IGNORECASE,
)
# Bare note letter — lowest priority fallback
KEY_BARE_RE = re.compile(
    r"(?:^|_)([A-G](?:#|b)?)(?=\.wav|_|$)",
    re.IGNORECASE,
)


NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Krumhansl-Schmuckler profiles for major and minor (used for template matching)
KS_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KS_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def _parse_from_filename(filename: str) -> Tuple[Optional[int], Optional[str]]:
    """Try to extract BPM and key from filename using regexes."""
    bpm = None
    key = None

    m = BPM_RE.search(filename)
    if m:
        try:
            bpm_group = next((g for g in m.groups() if g), None)
            bpm = int(bpm_group) if bpm_group else None
        except Exception:
            bpm = None

    m_full  = KEY_FULL_RE.search(filename)
    m_split = KEY_SPLIT_RE.search(filename)
    m_bare  = KEY_BARE_RE.search(filename)

    if m_full:
        raw = m_full.group(1)
    elif m_split:
        raw = m_split.group(1) + m_split.group(2)  # join note + mode
    elif m_bare:
        raw = m_bare.group(1)
    else:
        raw = None

    if raw:
        try:
            key = _normalize_key(raw)
        except Exception:
            key = None

    return bpm, key


def parse_filename(file_path: str) -> Tuple[Optional[int], Optional[str]]:
    """Public helper: parse BPM and key from a filename (or path).

    Returns (bpm, key) or (None, None) when not found.
    """
    import os

    filename = os.path.basename(file_path)
    return _parse_from_filename(filename)


def _normalize_key(raw: str) -> str:
    if not raw:
        return None
    
    raw = raw.strip()
    raw = raw.replace("minor", "min").replace("major", "maj")
    
    # Extract base note and accidental
    if len(raw) >= 1:
        base = raw[0].upper()
        accidental = ""
        suffix = raw[1:].lower() if len(raw) > 1 else ""
        
        if len(raw) >= 2 and raw[1] in ("#", "b"):
            accidental = raw[1]
            suffix = raw[2:].lower() if len(raw) > 2 else ""
        
        mode = ""
        if suffix.startswith("maj"):
            mode = " major"
        elif suffix.startswith("m"):
            mode = " minor"
        else:
            # Default to major if no explicit mode
            mode = " major"
        
        return f"{base}{accidental}{mode}".strip()
    
    return None


def _estimate_bpm(y: np.ndarray, sr: int) -> Optional[int]:
    try:
        import librosa

        n_fft = min(512, len(y))
        hop_length = n_fft // 4
        n_mels = min(64, n_fft // 2)
        onset_env = librosa.onset.onset_strength(
            y=y,
            sr=sr,
            n_fft=n_fft,
            hop_length=hop_length,
            n_mels=n_mels,
            fmax=sr / 2,
        )
        tempo, _ = librosa.beat.beat_track(onset_env=onset_env, sr=sr, hop_length=hop_length)
        return int(round(float(tempo))) if tempo is not None else None
    except Exception:
        return None


def _estimate_key(y: np.ndarray, sr: int) -> Optional[str]:
    try:
        import librosa

        n_fft = min(512, len(y))
        hop_length = n_fft // 4
        chroma = librosa.feature.chroma_stft(
            y=y,
            sr=sr,
            n_fft=n_fft,
            hop_length=hop_length,
        )
        key_idx = chroma.mean(axis=1).argmax()
        keys = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
        return keys[key_idx]
    except Exception:
        return None


def analyze_file(file_path: str) -> Tuple[Optional[int], Optional[str]]:
    """Return (bpm, audio_key) for a file.

    First attempts to extract values from the filename. If either value is
    missing, loads only the first 15 seconds via `librosa.load(..., duration=15, sr=11025)`
    and estimates missing values.
    """
    import os

    filename = os.path.basename(file_path)
    bpm, key = _parse_from_filename(filename)

    try:
        import librosa
    except Exception:
        return bpm, key

    if (bpm is not None and key is not None):
        return bpm, key

    # Load only the first 15 seconds at sr=11025
    try:
        y, sr = librosa.load(file_path, sr=11025, duration=15)
    except Exception:
        return bpm, key

    if bpm is None:
        bpm = _estimate_bpm(y, sr)

    if key is None:
        key = _estimate_key(y, sr)

    return bpm, key


def analyze_bpm(file_path: str) -> Optional[int]:
    """Analyze and return BPM only (loads first 15 seconds at sr=11025)."""
    try:
        import librosa
    except Exception:
        return None
    try:
        y, sr = librosa.load(file_path, sr=11025, duration=15)
    except Exception:
        return None
    return _estimate_bpm(y, sr)


def analyze_key(file_path: str) -> Optional[str]:
    """Analyze and return key only (loads first 15 seconds at sr=11025)."""
    try:
        import librosa
    except Exception:
        return None
    try:
        y, sr = librosa.load(file_path, sr=11025, duration=15)
    except Exception:
        return None
    return _estimate_key(y, sr)
