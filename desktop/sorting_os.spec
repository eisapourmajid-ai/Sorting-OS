# -*- coding: utf-8 -*-
"""PyInstaller specification for SORTING OS (Prompt 31).

Build command (on a machine that has PyInstaller installed):

    cd desktop
    python -m PyInstaller --noconfirm --clean sorting_os.spec

Notes:

* the target machine (Windows 7 SP1 x64) needs a Python build that still
  supports it — Python 3.8.10 is the last officially supported release;
* nothing is fetched from the network: no CDN assets, no fonts, no icons from
  the internet;
* the user data directory is *not* part of the bundle; it lives outside the
  installation (see ``sorting_os/paths.py``);
* the EXE is **not** verified in the environment where this spec was written —
  see ``docs/verification/target-os-verification.md``.
"""
import os

block_cipher = None

APP_NAME = "SortingOS"
ROOT = os.path.abspath(os.getcwd())

a = Analysis(
    ["run_app.py"],
    pathex=[ROOT],
    binaries=[],
    datas=[],
    hiddenimports=["sorting_os", "sorting_os.app", "sorting_os.ui.app"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["pytest", "numpy", "pandas", "matplotlib"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
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
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
)
