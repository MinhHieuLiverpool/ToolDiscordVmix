# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['vmix_monitor_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/Discord-Logo.ico', 'assets'), ('assets/Discord-Logo.png', 'assets'), ('config.py', '.')],
    hiddenimports=['PIL._tkinter_finder', 'pystray', 'PIL.Image', 'PIL.ImageDraw', 'pytz'],
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
    upx=True,
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
