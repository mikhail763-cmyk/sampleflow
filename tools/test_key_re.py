import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.audio_dsp import KEY_RE, _parse_from_filename

names = [
    "DS_VLUARR_126_percussion_loop_jungle_G.wav",
    "DS_MDH2_percussion_one_shot_chatty_D#.wav",
    "Kit_2_DS_Percussion_Loop_Fm_125.wav",
]

for n in names:
    m = KEY_RE.search(n)
    print(n)
    if m:
        print("  KEY_RE match:", m.group(0), "groups:", m.groups())
    else:
        print("  KEY_RE: NO MATCH")
    print("  _parse_from_filename:", _parse_from_filename(n))
    print()
