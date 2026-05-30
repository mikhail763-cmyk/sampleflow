"""Strip accumulated type/BPM prefixes from audio filenames and sync the DB.

Usage:
    python tools/fix_names.py [folder]

If folder is omitted the script will prompt for it.

Examples of names that get cleaned:
    Other_Other_Bass_Loop_120_Amin.wav  ->  Bass_Loop_120_Amin.wav
    FX_BPM140_riser_sweep.wav           ->  riser_sweep.wav
    Drums_Kick_kick_01.wav              ->  kick_01.wav
"""
from __future__ import annotations

import os
import re
import sys

# Make project root importable so we can reuse database helpers.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from app.core.database import rename_sample_path  # noqa: E402

# ---------------------------------------------------------------------------
# Prefix patterns — stripped repeatedly from the left until none remain.
#
# Only top-level category names that the old organizer prepended directly
# to filenames. Specific subtypes (Kick, Snare, Bass …) are intentionally
# excluded: they are often part of the original filename and stripping them
# would corrupt the name.
#
# "Drum Loop" and "Melody Loop" have a space — the old code joined parts
# with "_", producing "Drum Loop_original.wav".
# ---------------------------------------------------------------------------
_PREFIX_RE = re.compile(
    r"^(?:"
    r"Drum[\s_]Loop|Melody[\s_]Loop"  # space OR underscore between words
    r"|Other|Drums|Melodic"
    r"|FX|Vocal|Foley"
    r"|BPM\d+"                        # BPM120, BPM140, …
    r")_",
    re.IGNORECASE,
)

AUDIO_EXTS = {".wav", ".mp3", ".aiff", ".flac", ".ogg", ".aif"}


def strip_prefixes(stem: str) -> str:
    """Remove all leading known prefixes from a filename stem."""
    while True:
        cleaned = _PREFIX_RE.sub("", stem)
        if cleaned == stem:
            return stem
        stem = cleaned


def _unique_path(path: str) -> str:
    """Return a collision-free path by appending _1, _2, … if needed."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    counter = 1
    while True:
        candidate = f"{base}_{counter}{ext}"
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def process_folder(folder: str) -> int:
    fixed = 0
    skipped = 0

    for dirpath, _dirs, filenames in os.walk(folder):
        for filename in sorted(filenames):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in AUDIO_EXTS:
                continue

            stem, suffix = os.path.splitext(filename)
            new_stem = strip_prefixes(stem)

            if new_stem == stem:
                continue  # nothing to strip

            new_filename = new_stem + suffix
            old_path = os.path.join(dirpath, filename)
            new_path = os.path.join(dirpath, new_filename)

            if os.path.exists(new_path):
                new_path = _unique_path(new_path)

            try:
                os.rename(old_path, new_path)
            except OSError as exc:
                print(f"  ERROR  {filename}: {exc}")
                skipped += 1
                continue

            try:
                rename_sample_path(
                    os.path.abspath(old_path),
                    os.path.abspath(new_path),
                )
            except Exception as exc:
                print(f"  DB ERR {filename}: {exc}")

            rel = os.path.relpath(dirpath, folder)
            loc = "" if rel == "." else f"{rel}/"
            print(f"  {loc}{filename}")
            print(f"    -> {new_filename}")
            fixed += 1

    return fixed


def main() -> None:
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    else:
        folder = input("Folder to scan: ").strip().strip('"').strip("'")

    folder = os.path.abspath(folder)
    if not os.path.isdir(folder):
        print(f"Error: not a directory: {folder}")
        sys.exit(1)

    print(f"Scanning: {folder}\n")
    fixed = process_folder(folder)
    print(f"\nDone — {fixed} file(s) renamed.")


if __name__ == "__main__":
    main()
