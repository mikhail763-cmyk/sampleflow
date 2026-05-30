import os
import wave
import struct

outdir = os.path.join(os.path.dirname(__file__), 'sample_scan')
os.makedirs(outdir, exist_ok=True)

# write 1-second silent wav at 11025 Hz
def write_silence(path, duration=1.0, sr=11025):
    nframes = int(duration * sr)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        silence = struct.pack('<h', 0) * nframes
        wf.writeframes(silence)

write_silence(os.path.join(outdir, 'kick_120BPM.wav'), duration=1.0)
write_silence(os.path.join(outdir, 'loop_no_bpm.wav'), duration=1.0)
print('Created test audio in', outdir)
