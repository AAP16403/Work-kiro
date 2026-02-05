# -*- mode: python ; coding: utf-8 -*-
"""
Convenient PyInstaller spec for Privacy Screen Guard.

Usage:
  pyinstaller Blocksoft.spec

Toggles:
  - Edit ONEFILE / CONSOLE / ICON_FILE below as needed.
"""

from __future__ import annotations

import os
from pathlib import Path

block_cipher = None

# --- Build toggles ---
APP_NAME = "Blocksoft"
MAIN_SCRIPT = "Blocksoft.py"
ONEFILE = True
CONSOLE = False
UPX = True
ICON_FILE = "icon.ico"  # optional

HERE = Path(os.getcwd()).resolve()
SCRIPT_PATH = HERE / MAIN_SCRIPT
ICON_PATH = (HERE / ICON_FILE) if (HERE / ICON_FILE).exists() else None


def _try_collect_submodules(pkg: str):
    try:
        from PyInstaller.utils.hooks import collect_submodules

        return collect_submodules(pkg)
    except Exception:
        return []


hiddenimports = []
hiddenimports += _try_collect_submodules("PIL")
hiddenimports += _try_collect_submodules("pytesseract")
hiddenimports += _try_collect_submodules("pystray")

# Keep a few explicit ones for robustness
hiddenimports += [
    "tkinter",
    "PIL.ImageGrab",
]

a = Analysis(
    [str(SCRIPT_PATH)],
    pathex=[str(HERE)],
    binaries=[],
    datas=[],
    hiddenimports=sorted(set(hiddenimports)),
    hookspath=[],
    runtime_hooks=[],
    excludedimports=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=UPX,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=CONSOLE,
    icon=str(ICON_PATH) if ICON_PATH else None,
)

if not ONEFILE:
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=UPX,
        upx_exclude=[],
        name=APP_NAME,
    )
