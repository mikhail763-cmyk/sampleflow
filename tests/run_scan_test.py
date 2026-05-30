import os
import sys
from app.core.scanner import ScannerThread

p = os.path.join(os.path.dirname(__file__), 'sample_scan')
if not os.path.isdir(p):
    print('Test folder missing:', p)
    sys.exit(1)

st = ScannerThread(p)

st.sample_scanned.connect(lambda s: print('SCANNED:', s['file_name'], 'BPM=', s.get('bpm')))
st.analysis_started.connect(lambda fp: print('ANALYSIS STARTED:', fp))
st.analysis_completed.connect(lambda fp, bpm: print('ANALYSIS DONE:', fp, '-> BPM', bpm))
st.progress.connect(lambda n: print('PROGRESS:', n))
st.scan_started.connect(lambda total: print('SCAN STARTED total=', total))

# run synchronously
st.run()
print('Test scan finished')
