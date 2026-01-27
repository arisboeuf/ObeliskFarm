# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for ObeliskFarm Calculator
Build with: pyinstaller ObeliskFarm.spec
"""

import os
import re
from pathlib import Path

# Get the absolute path to the project root
PROJECT_ROOT = Path(SPECPATH)
OBELISK_DIR = PROJECT_ROOT / 'ObeliskGemEV'

# Version from __init__.py (parse only; avoid imports during spec execution)
_init_text = (OBELISK_DIR / '__init__.py').read_text(encoding='utf-8')
_m = re.search(r"^__version__\s*=\s*['\"]([^'\"]+)['\"]", _init_text, re.MULTILINE)
VERSION = _m.group(1) if _m else "0.0.0"

# Windows EXE icon: PyInstaller expects .ico on Windows. Generate one from the
# existing PNG (Pillow is already a project dependency).
ICON_PNG = OBELISK_DIR / 'sprites' / 'common' / 'gem.png'
ICON_ICO = OBELISK_DIR / 'sprites' / 'common' / 'gem.ico'
ICON_PATH = None
try:
    from PIL import Image

    if ICON_PNG.exists() and not ICON_ICO.exists():
        img = Image.open(ICON_PNG)
        img.save(
            ICON_ICO,
            format='ICO',
            sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
        )
    if ICON_ICO.exists():
        ICON_PATH = str(ICON_ICO)
except Exception:
    ICON_PATH = None

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
    icon=ICON_PATH,
)
