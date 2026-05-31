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

def test_detect_type_drum_loop():
    assert detect_type("drum_loop_120.wav") == "Drum Loop"

def test_detect_type_hihat():
    assert detect_type("hat_01.wav") == "Hi-Hat"

def test_detect_type_snare():
    assert detect_type("snare_dry_02.wav") == "Snare"

def test_detect_type_perc():
    assert detect_type("perc_01.wav") == "Perc"


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
# Test 1c — keyword additions from DB scan (2026-05-31)
# ---------------------------------------------------------------------------

# Metal Loop → Perc (African metal percussion, not drum loop)
def test_metal_loop_is_perc():
    assert detect_type("REA2_-_Metal_Loop_04_-_100Bpm.wav") == "Perc"

def test_metalloop_no_separator_is_perc():
    assert detect_type("PML_Organica_2_MetalLoop_004.wav") == "Perc"

# Key / key loop → Melodic (keyboard instrument)
def test_key_loop_is_melodic():
    assert detect_type("REA2_-_Key_Loop_03_-_105bpm_F_m.wav") == "Melodic"

def test_key_standalone_is_melodic():
    assert detect_type("MCT-AFT21-Key_18_120_-_B.wav") == "Melodic"

def test_key_with_number_no_separator_is_melodic():
    # "Key1" — no underscore between Key and 1, word boundary missing without fix
    assert detect_type("REA2_-_AfroBeat_09_-_Key1_100bpm_D_m.wav") == "Melodic"

def test_key2_no_separator_is_melodic():
    assert detect_type("REA2_-_AfroBeat_09_-_Key2_100bpm_D_m.wav") == "Melodic"

# KIT → Melodic (arrangement kit with key info)
def test_kit_is_melodic():
    assert detect_type("A_minor_04_KAHLE_KIT_Am_113bpm.wav") == "Melodic"

# Log Drum → Melodic (groove synth instrument)
def test_log_drum_is_melodic():
    assert detect_type("KAHLE_Log_Drum_Am_113bpm.wav") == "Melodic"

def test_log_drum_with_prefix_is_melodic():
    assert detect_type("RTDM_Gm_120BPM_De_Manh_-_Log_Drum.wav") == "Melodic"

# Mallet → Melodic (marimba/xylophone type)
def test_mallet_loop_is_melodic():
    assert detect_type("REA2_-_Mallet_Loop_01_-_100bpm_Em.wav") == "Melodic"

def test_ivory_is_melodic():
    assert detect_type("PL_APM_02_Ivory_100_Fmaj.wav") == "Melodic"

# Beat (standalone) → Melodic (full arrangement loop)
def test_beat_standalone_is_drum_loop():
    # Standalone "beat" (e.g. BEAT_01_B_126.wav) → Drum Loop, not Melodic
    assert detect_type("beat_120_Am.wav") == "Drum Loop"

def test_beat_prefix_is_drum_loop():
    assert detect_type("BEAT_01_B_126.wav") == "Drum Loop"

# Uplifter → FX
def test_uplifter_is_fx():
    assert detect_type("uplifter_riser.wav") == "FX"

# drum_top_loop → Drum Loop
def test_drum_top_loop_is_drum_loop():
    assert detect_type("009_120_drum_top_loop_sonic.wav") == "Drum Loop"

# drum_top (no loop) → Hi-Hat
def test_drum_top_is_hihat():
    assert detect_type("DS_VAH_119_drum_top_juice.wav") == "Hi-Hat"

# Perc plural forms
def test_percs_is_perc():
    assert detect_type("09_Percs_Loops_120.wav") == "Perc"

# percloop / perconeshot (concatenated, no separator)
def test_percloop_is_perc():
    assert detect_type("sample_percloop_01.wav") == "Perc"

def test_perconeshot_is_perc():
    assert detect_type("AU_AAS_perconeshot_abounding.wav") == "Perc"

# Drum fill → Perc
def test_drum_fill_is_perc():
    assert detect_type("HQ_DRUMS_Afro_House_Drum_Fill_01_120_BPM.wav") == "Perc"

def test_fill_loop_is_perc():
    assert detect_type("AU_LTH_drum_fill_carnal_wet.wav") == "Perc"

# Djembe → Perc
def test_djembe_is_perc():
    assert detect_type("DS_VAH_118_percussion_djembe_dalmatian.wav") == "Perc"

# Darbouka (variant spelling of darbuka) → Perc
def test_darbouka_is_perc():
    assert detect_type("DS_VAH_118_drum_fill_helenium_darbouka.wav") == "Perc"

# Melodic keyword: "melodic" (not just "melody")
def test_melodic_adjective_is_melodic():
    assert detect_type("BOS_AHH_120_Melodic_Stack_Loop_Ancestral_Am.wav") == "Melodic"

# Drum Loop: "drum_top_loop" via explicit pattern (regression)
def test_zenhiser_drum_top_loop_is_drum_loop():
    assert detect_type("009_120_drum_top_loop_sonic_BEDOUINMHT_Zenhiser.wav") == "Drum Loop"

# drums (plural, no other marker) → Perc
def test_drums_plural_is_perc():
    assert detect_type("HQ_DRUMS_Afro_House_Drum_Fill_01_120_BPM.wav") == "Perc"

# congaloop (no separator) → Perc
def test_congaloop_is_perc():
    assert detect_type("sample_congaloop_01.wav") == "Perc"

# otherperc (perc at word end) → Perc
def test_otherperc_is_perc():
    assert detect_type("ZEN_HIB_otherperc_oneshot.wav") == "Perc"

# afrobeat compound word → now caught by last-resort Melodic via \bafrobeat\b
def test_afrobeat_compound_is_melodic():
    assert detect_type("REA2_-_AfroBeat_09_-__Mix_100bpm_D_m.wav") == "Melodic"

# Breakbeat stays in Drum Loop (not moved to Melodic with "beat")
def test_breakbeat_is_drum_loop():
    assert detect_type("breakbeat_groove_01.wav") == "Drum Loop"


# ---------------------------------------------------------------------------
# Test 1d — priority conflict regression tests
# ---------------------------------------------------------------------------
# "beat" moved to last-resort Melodic so specific drum types win when present

def test_snare_beats_beat_keyword():
    # snare(priority 8) must win over beat→Melodic(6 previously, now last-resort)
    assert detect_type("snare_beat_01.wav") == "Snare"

def test_hihat_beats_beat_keyword():
    assert detect_type("hat_beat_01.wav") == "Hi-Hat"

def test_perc_beats_beat_keyword():
    assert detect_type("conga_beat.wav") == "Perc"

def test_drums_loop_is_drum_loop():
    # drums (plural) + loop → Drum Loop, not Perc
    assert detect_type("drums_loop_01.wav") == "Drum Loop"

def test_drums_full_loop_is_drum_loop():
    assert detect_type("ZEN_120_drums_full_loop_main.wav") == "Drum Loop"

# Higher-priority types beat lower ones correctly
def test_piano_beats_break():
    # piano=Melodic(6) beats break=DrumLoop(7)
    assert detect_type("piano_break.wav") == "Melodic"

def test_piano_beats_fill():
    # piano=Melodic(6) beats fill=Perc(11)
    assert detect_type("piano_fill.wav") == "Melodic"

def test_kick_beats_drums():
    # kick=Kick(3) beats drums=Perc(11)
    assert detect_type("kick_drums.wav") == "Kick"

def test_bass_beats_fill():
    # bass=Bass(4) beats fill=Perc(11)
    assert detect_type("bass_fill_01.wav") == "Bass"

def test_fx_beats_beat():
    # fx=FX(2) beats beat=last-resort Melodic
    assert detect_type("REA2_-_AfroBeat_09_-_Fx_100bpm.wav") == "FX"

def test_kick_beats_beat():
    # kick=Kick(3) beats beat=last-resort Melodic
    assert detect_type("REA2_-_AfroBeat_09_-_Kick_100bpm.wav") == "Kick"

def test_shaker_beats_beat():
    # shaker=Perc(11) beats beat=last-resort Melodic
    assert detect_type("REA2_-_AfroBeat_07_-_Shaker_105bpm.wav") == "Perc"

# groove is Drum Loop and beats lower-priority types — documented expected behavior
def test_groove_is_drum_loop():
    assert detect_type("groove_01.wav") == "Drum Loop"

def test_groove_with_snare_is_drum_loop():
    # groove(DrumLoop=7) beats snare(Snare=8) — groove loop with snare sound
    assert detect_type("groove_snare.wav") == "Drum Loop"


# ---------------------------------------------------------------------------
# Test 1e — key parsing edge cases (underscore-split note+mode)
# ---------------------------------------------------------------------------

def test_key_f_m_split():
    # F_m = F minor; KEY_SPLIT_RE must handle underscore-separated note+mode
    assert _parse_from_filename("RTAH3_SQS_118_F_m_Melody.wav")[1] == "F minor"

def test_key_a_minor_split():
    assert _parse_from_filename("loop_A_minor_120.wav")[1] == "A minor"

def test_key_d_min_split():
    assert _parse_from_filename("loop_D_min_120.wav")[1] == "D minor"

def test_key_c_major_split():
    assert _parse_from_filename("loop_C_major_120.wav")[1] == "C major"

def test_key_bb_maj_split():
    assert _parse_from_filename("loop_Bb_maj_120.wav")[1] == "Bb major"

def test_key_full_re_wins_over_split():
    # "Am" compact form beats "A_minor" split form — KEY_FULL_RE has priority
    bpm, key = _parse_from_filename("A_minor_04_KAHLE_KIT_Am_113bpm.wav")
    assert key == "A minor"

def test_key_no_false_positive_from_codename():
    # "DS_MYRNE" contains D — must NOT extract "D major" as key
    assert _parse_from_filename("DS_MYRNE_120_drum_full_loop_driving.wav")[1] is None

def test_bpm_range_low():
    # 79 BPM is below the 80-200 accepted range
    assert _parse_from_filename("79bpm_loop.wav")[0] is None

def test_bpm_range_high():
    # 205 BPM is above the 80-200 accepted range
    assert _parse_from_filename("loop_205BPM.wav")[0] is None

def test_key_bbmaj():
    assert _parse_from_filename("loop_Bbmaj.wav")[1] == "Bb major"

def test_key_fsharp_minor():
    assert _parse_from_filename("loop_F#m.wav")[1] == "F# minor"

def test_key_ebmin():
    assert _parse_from_filename("loop_Ebmin.wav")[1] == "Eb minor"


# ---------------------------------------------------------------------------
# Test 1f — organization edge cases
# ---------------------------------------------------------------------------

def test_organize_unknown_type_goes_to_other(tmp_path):
    from app.core.organizer import organize_files
    import os

    src = tmp_path / "src"
    src.mkdir()
    out = tmp_path / "out"
    out.mkdir()

    f = src / "mystery_01.wav"
    f.write_bytes(b"\x00" * 1024)

    samples = [{"file_path": str(f), "sample_type": None, "audio_key": None}]
    organize_files(samples, str(out))

    assert (out / "Other").is_dir()
    assert any((out / "Other").iterdir())

def test_organize_vocal_no_key_goes_to_unknown(tmp_path):
    from app.core.organizer import organize_files
    import os

    src = tmp_path / "src"
    src.mkdir()
    out = tmp_path / "out"
    out.mkdir()

    f = src / "vocal_dry_01.wav"
    f.write_bytes(b"\x00" * 1024)

    samples = [{"file_path": str(f), "sample_type": "Vocal", "audio_key": None}]
    organize_files(samples, str(out))

    assert (out / "Vocal" / "Unknown").is_dir()

def test_organize_fx_goes_flat(tmp_path):
    from app.core.organizer import organize_files

    src = tmp_path / "src"
    src.mkdir()
    out = tmp_path / "out"
    out.mkdir()

    f = src / "riser_01.wav"
    f.write_bytes(b"\x00" * 1024)

    samples = [{"file_path": str(f), "sample_type": "FX", "audio_key": None}]
    organize_files(samples, str(out))

    # FX is a FLAT_TYPE — goes directly to out/FX/, no key subfolder
    assert (out / "FX").is_dir()
    assert not (out / "FX" / "Unknown").exists()

def test_organize_drum_loop_hierarchical(tmp_path):
    from app.core.organizer import organize_files

    src = tmp_path / "src"
    src.mkdir()
    out = tmp_path / "out"
    out.mkdir()

    f = src / "drum_loop_Am_120.wav"
    f.write_bytes(b"\x00" * 1024)

    samples = [{"file_path": str(f), "sample_type": "Drum Loop", "audio_key": "A minor"}]
    organize_files(samples, str(out))

    assert (out / "Drums" / "Drum Loop" / "A minor").is_dir()

def test_organize_skips_file_already_in_output(tmp_path):
    from app.core.organizer import organize_files

    out = tmp_path / "out"
    (out / "Drums" / "Kick" / "Unknown").mkdir(parents=True)
    f = out / "Drums" / "Kick" / "Unknown" / "kick_01.wav"
    f.write_bytes(b"\x00" * 1024)

    samples = [{"file_path": str(f), "sample_type": "Kick", "audio_key": None}]
    moved = organize_files(samples, str(out))

    # File is inside output_dir — must be skipped
    assert moved == 0
    assert f.exists()

def test_organize_skips_missing_file(tmp_path):
    from app.core.organizer import organize_files

    out = tmp_path / "out"
    out.mkdir()

    samples = [{"file_path": str(tmp_path / "ghost.wav"), "sample_type": "Kick", "audio_key": None}]
    moved = organize_files(samples, str(out))

    assert moved == 0

def test_organize_melody_loop_hierarchical(tmp_path):
    from app.core.organizer import organize_files

    src = tmp_path / "src"
    src.mkdir()
    out = tmp_path / "out"
    out.mkdir()

    f = src / "melody_loop_Dm.wav"
    f.write_bytes(b"\x00" * 1024)

    samples = [{"file_path": str(f), "sample_type": "Melody Loop", "audio_key": "D minor"}]
    organize_files(samples, str(out))

    assert (out / "Melodic" / "Melody Loop" / "D minor").is_dir()


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
