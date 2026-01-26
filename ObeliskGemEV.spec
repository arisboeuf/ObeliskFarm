# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for ObeliskFarm Calculator
Build with: pyinstaller ObeliskFarm.spec
"""

import os
from pathlib import Path

# Get the absolute path to the project root
PROJECT_ROOT = Path(SPECPATH)
OBELISK_DIR = PROJECT_ROOT / 'ObeliskFarm'

# Version from __init__.py
exec(open(OBELISK_DIR / '__init__.py').read())
VERSION = __version__

a = Analysis(
    [str(OBELISK_DIR / 'gui.py')],
    pathex=[str(OBELISK_DIR)],
    binaries=[],
    datas=[
        # Include all sprites
        (str(OBELISK_DIR / 'sprites'), 'sprites'),
    ],
    hiddenimports=[
        'PIL._tkinter_finder',
        'matplotlib.backends.backend_tkagg',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f'ObeliskFarm_v{VERSION}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(OBELISK_DIR / 'sprites' / 'common' / 'gem.png'),
)
