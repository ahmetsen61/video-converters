"""
ffmpeg_utils.py
---------------
FFmpeg binary konumunu tespit eder.
- PyInstaller ile paketlenmiş exe'de sys._MEIPASS altında arar
- Geliştirme ortamında assets/ffmpeg/ altında arar
- Son çare olarak sistem PATH'ini kullanır
"""

import os
import sys
import shutil


def _get_base_path() -> str:
    """PyInstaller paketi veya geliştirme dizinini döndürür."""
    if getattr(sys, 'frozen', False):
        # PyInstaller --onefile: _MEIPASS geçici dizini
        return sys._MEIPASS
    # Geliştirme: proje kök dizini
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_ffmpeg_path() -> str:
    """ffmpeg.exe yolunu döndürür. Bulunamazsa 'ffmpeg' döner (PATH'ten)."""
    base = _get_base_path()

    candidates = [
        os.path.join(base, "ffmpeg", "ffmpeg.exe"),          # PyInstaller içi
        os.path.join(base, "assets", "ffmpeg", "ffmpeg.exe"), # Geliştirme
    ]

    for path in candidates:
        if os.path.isfile(path):
            return path

    # Son çare: sistem PATH
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    return "ffmpeg"  # Bulunamazsa komut olarak dene


def get_ffprobe_path() -> str:
    """ffprobe.exe yolunu döndürür."""
    base = _get_base_path()

    candidates = [
        os.path.join(base, "ffmpeg", "ffprobe.exe"),
        os.path.join(base, "assets", "ffmpeg", "ffprobe.exe"),
    ]

    for path in candidates:
        if os.path.isfile(path):
            return path

    system_ffprobe = shutil.which("ffprobe")
    if system_ffprobe:
        return system_ffprobe

    return "ffprobe"


def is_ffmpeg_available() -> bool:
    """FFmpeg'in kullanılabilir olup olmadığını kontrol eder."""
    import subprocess
    try:
        path = get_ffmpeg_path()
        result = subprocess.run(
            [path, "-version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False
