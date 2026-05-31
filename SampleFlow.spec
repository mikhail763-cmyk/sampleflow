# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_data_files

datas = [("assets", "assets")]
binaries = []
hiddenimports = []

# librosa pulls in numba, llvmlite, scipy, sklearn — collect everything
for pkg in ("librosa", "numba", "numba.core", "resampy", "audioread"):
    d, b, h = collect_all(pkg)
    datas    += d
    binaries += b
    hiddenimports += h

# soundfile needs its native CFFI extension collected explicitly
d, b, h = collect_all("soundfile")
datas    += d
binaries += b
hiddenimports += h

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + [
        "PyQt6.sip",
        "scipy.signal",
        "scipy.fft",
        "scipy._lib.array_api_compat.numpy.fft",
        "sklearn.utils._cython_blas",
        "sklearn.neighbors._partition_nodes",
        "sklearn.neighbors.typedefs",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "IPython", "jupyter", "notebook", "matplotlib"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SampleFlow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon="assets/icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="SampleFlow",
)
