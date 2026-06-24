# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['pomodoro.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('ringtone.mp3', '.'),
        ('pomodoro.ico', '.'),
    ],
    hiddenimports=['PyQt6.sip'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='番茄鐘',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon='pomodoro.ico',
)
