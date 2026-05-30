"""Core unit tests for SampleFlow.

Run with:
    python -m pytest tests/test_core.py -v
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.audio_dsp import _parse_from_filename
from app.core.organizer import detect_type


# ---------------------------------------------------------------------------
# Test 1 — type detection by filename keywords
# ---------------------------------------------------------------------------

def test_detect_type_kick():
    assert detect_type("kick_01.wav") == "Kick"

def test_detect_type_bass_loop():
    assert detect_type("bass_loop_120.wav") == "Bass"

def test_detect_type_vocal():
    assert detect_type("91V_FF_vocal_one_shot.wav") == "Vocal"

def test_detect_type_fx():
    assert detect_type("riser_sweep_fx.wav") == "FX"

def test_detect_type_unknown():
    assert detect_type("1.mp3") == "Other"


# ---------------------------------------------------------------------------
# Test 1b — Kick must win over Bass (priority fix)
# ---------------------------------------------------------------------------

def test_kick_beats_bass():
    assert detect_type("bass_kick.wav") == "Kick"

def test_bass_drum_is_kick():
    assert detect_type("bass_drum_01.wav") == "Kick"

def test_pure_bass_stays_bass():
    assert detect_type("bass_loop.wav") == "Bass"

def test_808_is_bass():
    assert detect_type("808_sub.wav") == "Bass"


# ---------------------------------------------------------------------------
# Test 2 — BPM parsing from filename
# ---------------------------------------------------------------------------

def test_bpm_underscore():
    assert _parse_from_filename("track_120_Am.wav")[0] == 120

def test_bpm_parentheses():
    assert _parse_from_filename("Beat (140 BPM).wav")[0] == 140

def test_bpm_missing():
    assert _parse_from_filename("1.mp3")[0] is None


# ---------------------------------------------------------------------------
# Test 3 — key parsing from filename
# ---------------------------------------------------------------------------

def test_key_amin():
    assert _parse_from_filename("loop_Amin.wav")[1] == "A minor"

def test_key_fmaj():
    assert _parse_from_filename("bass_Fmaj.wav")[1] == "F major"

def test_key_missing():
    assert _parse_from_filename("kick_01.wav")[1] is None


# ---------------------------------------------------------------------------
# Test 4 — database round-trip (uses tmp_path fixture, no disk side-effects)
# ---------------------------------------------------------------------------

def test_database_insert_and_fetch(tmp_path):
    from app.core import database

    db = str(tmp_path / "test.db")
    database.init_db(db)
    database.insert_sample(
        file_path="/fake/kick.wav",
        file_name="kick.wav",
        file_size=99_999,
        file_hash="abc123",
        bpm=120,
        audio_key="C major",
        is_duplicate=0,
        sample_type="Kick",
        path=db,
    )

    row = database.fetch_sample(file_path="/fake/kick.wav", path=db)
    assert row is not None
    assert row["bpm"] == 120
    assert row["audio_key"] == "C major"
    assert row["sample_type"] == "Kick"


def test_update_sample_type(tmp_path):
    from app.core import database

    db = str(tmp_path / "test.db")
    database.init_db(db)
    database.insert_sample(
        file_path="/fake/loop.wav",
        file_name="loop.wav",
        file_size=50_000,
        file_hash="def456",
        path=db,
    )

    database.update_sample_type("/fake/loop.wav", "Drum Loop", path=db)
    row = database.fetch_sample(file_path="/fake/loop.wav", path=db)
    assert row["sample_type"] == "Drum Loop"


def test_insert_does_not_overwrite_manual_type(tmp_path):
    """Re-scanning must not clobber a manually-set sample_type."""
    from app.core import database

    db = str(tmp_path / "test.db")
    database.init_db(db)

    database.insert_sample(
        file_path="/fake/pad.wav", file_name="pad.wav",
        file_size=50_000, file_hash="ghi", path=db,
    )
    database.update_sample_type("/fake/pad.wav", "Pad", path=db)

    # Re-insert with sample_type=None (simulates re-scan without keyword match)
    database.insert_sample(
        file_path="/fake/pad.wav", file_name="pad.wav",
        file_size=50_000, file_hash="ghi", sample_type=None, path=db,
    )
    row = database.fetch_sample(file_path="/fake/pad.wav", path=db)
    assert row["sample_type"] == "Pad"  # manual value preserved


def test_delete_missing_files(tmp_path):
    from app.core import database

    db = str(tmp_path / "test.db")
    database.init_db(db)
    database.insert_sample(
        file_path="/nonexistent/ghost.wav", file_name="ghost.wav",
        file_size=50_000, file_hash="xyz", path=db,
    )
    removed = database.delete_missing_files(path=db)
    assert removed == 1
    assert database.fetch_sample(file_path="/nonexistent/ghost.wav", path=db) is None


# ---------------------------------------------------------------------------
# Test 5 — syntax-check every .py file in the project
# ---------------------------------------------------------------------------

def test_compile_all_sources():
    import glob
    import py_compile

    base = os.path.dirname(os.path.dirname(__file__))
    files = glob.glob(os.path.join(base, "app", "**", "*.py"), recursive=True)
    main_py = os.path.join(base, "main.py")
    if os.path.exists(main_py):
        files.append(main_py)

    for f in files:
        py_compile.compile(f, doraise=True)
