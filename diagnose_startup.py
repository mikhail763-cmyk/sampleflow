import subprocess
import sys

p = subprocess.Popen([sys.executable, '-u', 'main.py'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
try:
    out, _ = p.communicate(timeout=20)
except subprocess.TimeoutExpired:
    p.kill()
    out, _ = p.communicate()
print(out)