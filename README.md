# 🎵 SampleFlow v2.0

> ⚠️ **Work in Progress** — the app is functional but still in active development. Bugs are expected. Always keep backups of your samples before organizing.

> A lightweight desktop app for organizing and cleaning your music sample library.

![SampleFlow](https://img.shields.io/badge/version-2.0-00ADB5?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10+-00ADB5?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Windows-00ADB5?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-00ADB5?style=flat-square)

---

## What it does

SampleFlow scans your sample folders, detects BPM and key from filenames or audio analysis, finds duplicates, and organizes everything into a clean folder structure — automatically.

---

## Features

- 🔍 **Smart scanning** — reads BPM and key from filenames instantly
- 🎼 **Audio analysis** — detects key via librosa when filename has no info
- 🧠 **Type detection** — identifies Kick, Snare, Bass, Vocal, FX and more
- 📁 **Auto-organize** — moves files into structured folders by type and key
- 🔁 **Duplicate finder** — finds exact duplicates via fast file hashing
- ✏️ **Manual override** — edit type directly in the table with a double-click
- 🌐 **EN / RU** — switch language without restarting
- 🎨 **Dark UI** — clean dark theme optimized for long sessions

---

## Output folder structure

```
Output/
├── Drums/
│   ├── Kick/
│   │   ├── A minor/
│   │   └── Unknown/
│   ├── Snare/
│   ├── Hi-Hat/
│   ├── Perc/
│   └── Drum Loop/
├── Melodic/
│   ├── Bass/
│   ├── Lead/
│   ├── Melodic/
│   └── Melody Loop/
├── Vocal/
│   ├── C minor/
│   └── Unknown/
├── FX/
└── Other/
```

---

## Requirements

- Windows 10 / 11
- Python 3.10+
- pip

---

## Installation

```bash
git clone https://github.com/mienko/sampleflow.git
cd sampleflow
pip install -r requirements.txt
python main.py
```

---

## How to use

1. **Choose Folder** — select your samples folder
2. **Scan** — app scans files, detects BPM, key and type automatically
3. **Detect Key** — analyze key for files without one (optional)
4. **Organize** — choose output folder, files move into clean structure

---

## Tech stack

| Library | Purpose |
|---------|---------|
| PyQt6 | Desktop UI |
| librosa | Audio analysis (BPM, key, type) |
| soundfile | Fast audio file reading |
| SQLite (WAL) | Local database |
| numpy | Math operations |

---

## Author

**Developer & Artist: mi:Enko**

© 2026 All rights reserved

---

## License

MIT License — free to use, modify and distribute with attribution.
