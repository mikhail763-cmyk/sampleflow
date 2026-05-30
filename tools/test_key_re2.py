import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.core.audio_dsp import KEY_RE, _parse_from_filename

names = [
    'DS_MYRNE_vocal_adlib_female_in_time_ah_wet_Ebmaj.wav',
    'DS_MYRNE_vocal_adlib_female_maze_high_dry_Bbmaj.wav',
    'DS_MYRNE_vocal_adlib_female_underground_dry_F#min.wav',
]

for n in names:
    m = KEY_RE.search(n)
    print(n)
    print('  KEY_RE:', m.group(0) if m else 'NO MATCH', 'groups:', m.groups() if m else None)
    print('  parse:', _parse_from_filename(n))
