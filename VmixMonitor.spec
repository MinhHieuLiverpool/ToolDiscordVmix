# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['PIL._tkinter_finder', 'pystray', 'PIL.Image', 'PIL.ImageDraw', 'pytz']
hiddenimports += collect_submodules('vmix_monitor_gui')


a = Analysis(
    ['vmix_monitor_gui\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/Discord-Logo.ico', 'assets'), ('assets/Discord-Logo.png', 'assets'), ('config.py', '.')],
    hiddenimports=hiddenimports,
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
    name='VmixMonitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\Discord-Logo.ico'],
)
