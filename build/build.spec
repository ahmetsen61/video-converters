# -*- mode: python ; coding: utf-8 -*-
"""
build.spec
----------
PyInstaller spec dosyasi.
Tek .exe ciktisi uretir, FFmpeg binary'sini icine gomer.

Kullanim (proje kok dizininden):
    venv\Scripts\python -m PyInstaller build\build.spec --clean --noconfirm

Cikti: dist\VideoConverter.exe
"""

import os
import sys

# Proje kok dizini: bu spec dosyasi build/ icinde,
# dolayisiyla bir ust dizin proje kokundur.
ROOT = os.path.abspath(os.path.join(os.path.dirname(SPECPATH), ''))

# FFmpeg binary yollari
FFMPEG_DIR  = os.path.join(ROOT, 'assets', 'ffmpeg')
FFMPEG_EXE  = os.path.join(FFMPEG_DIR, 'ffmpeg.exe')
FFPROBE_EXE = os.path.join(FFMPEG_DIR, 'ffprobe.exe')

# Binary listesi
binaries = []
if os.path.isfile(FFMPEG_EXE):
    binaries.append((FFMPEG_EXE, 'ffmpeg'))
    print(f'[spec] ffmpeg.exe eklendi: {FFMPEG_EXE}')
else:
    print(f'[spec] UYARI: ffmpeg.exe bulunamadi: {FFMPEG_EXE}')

if os.path.isfile(FFPROBE_EXE):
    binaries.append((FFPROBE_EXE, 'ffmpeg'))
    print(f'[spec] ffprobe.exe eklendi: {FFPROBE_EXE}')
else:
    print(f'[spec] UYARI: ffprobe.exe bulunamadi: {FFPROBE_EXE}')

# QSS tema dosyalari (frontend/styles/) ve UI ikonlari
datas = [
    (os.path.join(ROOT, 'frontend', 'styles', 'dark_theme.qss'),  'frontend/styles'),
    (os.path.join(ROOT, 'frontend', 'styles', 'light_theme.qss'), 'frontend/styles'),
    (os.path.join(ROOT, 'assets', 'icons'), 'assets/icons'),
]

# Uygulama ikonu (varsa)
icon_path = os.path.join(ROOT, 'assets', 'app_icon.ico')
icon_arg  = icon_path if os.path.isfile(icon_path) else None

# Gizli importlar (yt-dlp dinamik yukleme yapar, sqlite3 gecmis icin)
hidden_imports = [
    'sqlite3',
    'yt_dlp',
    'yt_dlp.extractor',
    'yt_dlp.extractor.youtube',
    'yt_dlp.extractor.instagram',
    'yt_dlp.extractor.tiktok',
    'yt_dlp.utils',
    'yt_dlp.postprocessor',
    'yt_dlp.postprocessor.ffmpeg',
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
]

# Ana script
MAIN_SCRIPT = os.path.join(ROOT, 'main.py')

a = Analysis(
    [MAIN_SCRIPT],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
        'test',
        'unittest',
        'xmlrpc',
        'doctest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VideoConverter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # Konsol penceresi gosterme
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_arg,
)
