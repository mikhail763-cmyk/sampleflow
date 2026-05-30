#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Rescan all samples in database and update BPM/Key with improved parsing."""
from __future__ import annotations

import sys
import io
from app.core import database, audio_dsp

# Fix encoding for console output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def main() -> int:
    database.init_db()
    samples = database.query_samples(search=None, duplicates_only=False)
    
    if not samples:
        print("No samples found in database.")
        return 0
    
    total = len(samples)
    updated = 0
    
    print(f"Rescanning {total} samples...")
    
    for idx, row in enumerate(samples, 1):
        file_path = row["file_path"]
        file_name = row["file_name"]
        
        # Parse with new regexes
        bpm, key = audio_dsp.parse_filename(file_path)
        
        # Check if anything changed
        changed = False
        if bpm is not None and bpm != row["bpm"]:
            changed = True
        if key is not None and key != row["audio_key"]:
            changed = True
        
        if changed:
            database.update_sample_by_path(file_path, bpm=bpm, audio_key=key)
            updated += 1
            print(f"  [{idx}/{total}] {file_name}: BPM={bpm}, Key={key}")
        else:
            print(f"  [{idx}/{total}] {file_name}: No change")
    
    print(f"\nRescan complete: {updated}/{total} samples updated.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
