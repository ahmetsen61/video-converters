"""
downloader.py
-------------
İndirme işçisi. QThread tabanlı, yt-dlp ile asenkron indirme yapar.
Her indirme görevi ayrı bir DownloadWorker thread'inde çalışır.

Sinyaller:
    progress(int)        - 0-100 arası ilerleme yüzdesi
    speed(str)           - "2.5 MB/s" gibi hız metni
    eta(str)             - "00:45" gibi kalan süre metni
    status(str)          - Durum metni
    finished(str)        - Tamamlanan dosya yolu
    error(str)           - Hata mesajı
    thumbnail_ready(str) - Thumbnail URL (analiz sonrası)
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import yt_dlp
from PyQt6.QtCore import QThread, pyqtSignal

from backend.ffmpeg_utils import get_ffmpeg_path


class DownloadStatus(Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    DOWNLOADING = "downloading"
    CONVERTING = "converting"
    FINISHED = "finished"
    ERROR = "error"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class DownloadTask:
    """Tek bir indirme görevini temsil eder."""
    url: str
    output_dir: str
    format_type: str = "mp4"          # "mp4" veya "mp3"
    quality: str = "best"              # "4K", "1080p", "720p", "best", "bestaudio"
    quality_height: Optional[int] = None  # Piksel cinsinden yükseklik (1080, 720, ...)
    format_id: Optional[str] = None    # yt-dlp format_id
    mp3_bitrate: str = "320"           # "128", "192", "256", "320"
    task_id: str = ""
    title: str = ""
    thumbnail_url: str = ""
    platform: str = "unknown"

    def __post_init__(self):
        if not self.task_id:
            import uuid
            self.task_id = str(uuid.uuid4())[:8]


def _format_speed(bytes_per_sec: float | None) -> str:
    """Hızı okunabilir formata çevirir."""
    if not bytes_per_sec:
        return "—"
    if bytes_per_sec < 1024:
        return f"{bytes_per_sec:.0f} B/s"
    elif bytes_per_sec < 1024 * 1024:
        return f"{bytes_per_sec / 1024:.1f} KB/s"
    else:
        return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"


def _format_eta(seconds: int | None) -> str:
    """ETA'yı MM:SS formatına çevirir."""
    if seconds is None or seconds < 0:
        return "—"
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _build_format_selector(task: DownloadTask) -> str:
    """yt-dlp format seçici string'i oluşturur."""
    if task.format_type == "mp3":
        return "bestaudio/best"

    # Eğer spesifik bir format_id seçilmişse, onu kullan (video ise audio ile birleştir)
    if task.format_id:
        return f"{task.format_id}+bestaudio/best"

    # MP4 için kalite seçimi
    h = task.quality_height

    if h is None or task.quality == "best":
        # En iyi kalite — video+ses birleşik veya ayrı stream
        return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"

    # Belirli bir yükseklik için
    return (
        f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/"
        f"bestvideo[height<={h}]+bestaudio/"
        f"best[height<={h}]/"
        f"best"
    )


class DownloadWorker(QThread):
    """
    Tek bir video/ses indirme işlemini arka planda yürüten QThread.

    Kullanım:
        task = DownloadTask(url="...", output_dir="...", format_type="mp4")
        worker = DownloadWorker(task)
        worker.progress.connect(progress_bar.setValue)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        worker.start()
    """

    progress = pyqtSignal(int)          # 0-100
    speed = pyqtSignal(str)
    eta = pyqtSignal(str)
    status = pyqtSignal(str)
    finished = pyqtSignal(str)          # dosya yolu
    error = pyqtSignal(str)             # hata mesajı
    title_found = pyqtSignal(str)       # video başlığı

    def __init__(self, task: DownloadTask, parent=None):
        super().__init__(parent)
        self.task = task
        self._cancelled = False
        self._last_progress = 0

    def cancel(self):
        """İndirmeyi iptal eder."""
        self._cancelled = True
        self.requestInterruption()

    def _progress_hook(self, d: dict):
        """yt-dlp ilerleme callback'i."""
        if self._cancelled or self.isInterruptionRequested():
            raise yt_dlp.utils.DownloadError("İptal edildi.")

        status = d.get("status", "")

        if status == "downloading":
            # İlerleme yüzdesi
            pct_str = d.get("_percent_str", "0%").strip().replace("%", "")
            try:
                pct = int(float(pct_str))
            except ValueError:
                pct = self._last_progress

            # Bazen yt-dlp 100'ü geçebilir, sınırla
            pct = max(0, min(pct, 99))
            self._last_progress = pct
            self.progress.emit(pct)

            # Hız
            speed_val = d.get("speed")
            self.speed.emit(_format_speed(speed_val))

            # ETA
            eta_val = d.get("eta")
            self.eta.emit(_format_eta(eta_val))

            self.status.emit("İndiriliyor...")

        elif status == "error":
            self.status.emit("Hata oluştu")

    def _postprocessor_hook(self, d: dict):
        """FFmpeg dönüştürme aşaması callback'i."""
        if d.get("status") == "started":
            self.status.emit("Dönüştürülüyor... (FFmpeg)")
            self.progress.emit(99)

    def run(self):
        """Thread içinde indirme işlemini başlatır."""
        task = self.task

        # Çıktı klasörünü oluştur
        os.makedirs(task.output_dir, exist_ok=True)

        # Çıktı dosya adı şablonu
        output_template = os.path.join(
            task.output_dir,
            "%(title)s [%(id)s].%(ext)s"
        )

        ffmpeg_path = get_ffmpeg_path()
        format_selector = _build_format_selector(task)
        
        print(f"[downloader] Running task {task.task_id}: format_type={task.format_type}, quality_height={task.quality_height}, format_id={task.format_id}, mp3_bitrate={task.mp3_bitrate}, selector={format_selector}")

        ydl_opts: dict = {
            "format": format_selector,
            "outtmpl": output_template,
            "ffmpeg_location": ffmpeg_path,
            "progress_hooks": [self._progress_hook],
            "postprocessor_hooks": [self._postprocessor_hook],
            "quiet": True,
            "no_warnings": True,
            "retries": 3,
            "fragment_retries": 5,
            "concurrent_fragment_downloads": 4,  # Parçaları paralel indir
            "merge_output_format": "mp4" if task.format_type == "mp4" else None,
            "writethumbnail": False,
            "writeinfojson": False,
        }

        # MP3 için ses dönüştürücü
        if task.format_type == "mp3":
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": task.mp3_bitrate,
                }
            ]

        # Gerçek indirme başlangıcında durum güncelle
        self.status.emit("Başlatılıyor...")
        self.progress.emit(0)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Önce meta veri al (başlık için)
                if not task.title:
                    try:
                        info = ydl.extract_info(task.url, download=False)
                        if info and info.get("title"):
                            self.title_found.emit(info["title"])
                    except Exception:
                        pass

                if self._cancelled:
                    return

                # İndir
                ydl.download([task.url])

        except yt_dlp.utils.DownloadError as e:
            err = str(e)
            if "İptal" in err or "cancelled" in err.lower():
                self.status.emit("İptal edildi")
                return
            if "private" in err.lower() or "login" in err.lower():
                self.error.emit("Bu video özel veya kısıtlıdır.")
                return
            if "not available" in err.lower():
                self.error.emit("Video mevcut değil veya kaldırılmış.")
                return
            if "network" in err.lower() or "connection" in err.lower():
                self.error.emit("Bağlantı hatası. İnternet bağlantınızı kontrol edin.")
                return
            self.error.emit(f"İndirme hatası: {err[:200]}")
            return
        except Exception as e:
            if self._cancelled:
                self.status.emit("İptal edildi")
                return
            self.error.emit(f"Beklenmeyen hata: {str(e)[:200]}")
            return

        # Tamamlandı — dosyayı bul
        self.progress.emit(100)
        self.status.emit("Tamamlandı!")

        # En son değiştirilen dosyayı bul (indirilen dosya)
        output_file = self._find_output_file(task.output_dir)
        self.finished.emit(output_file or task.output_dir)

    def _find_output_file(self, directory: str) -> str | None:
        """İndirme sonrası oluşan dosyayı tespit eder."""
        try:
            files = [
                os.path.join(directory, f)
                for f in os.listdir(directory)
                if os.path.isfile(os.path.join(directory, f))
                and f.endswith((".mp4", ".mp3", ".mkv", ".webm", ".m4a"))
            ]
            if not files:
                return None
            # En son oluşturulanı döndür
            return max(files, key=os.path.getctime)
        except Exception:
            return None