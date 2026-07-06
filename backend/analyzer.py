"""
analyzer.py
-----------
URL analiz motoru. yt-dlp kullanarak verilen URL'deki
video/ses formatlarını ve meta verileri çeker.

Döndürdüğü veri yapısı:
{
    "title": str,
    "uploader": str,
    "duration": int,  # saniye
    "thumbnail": str,  # URL
    "platform": str,  # "youtube" | "instagram" | "tiktok" | "unknown"
    "is_playlist": bool,
    "playlist_count": int | None,
    "formats": [
        {
            "format_id": str,
            "ext": str,
            "quality_label": str,  # "4K", "1440p", "1080p", ...
            "resolution": str,     # "3840x2160"
            "fps": int | None,
            "vcodec": str,
            "acodec": str,
            "filesize": int | None,  # bytes
            "is_audio_only": bool,
        }
    ],
    "entries": [...]  # Playlist ise içerik listesi
}
"""

from __future__ import annotations

import re
from typing import Any

import yt_dlp

from backend.ffmpeg_utils import get_ffmpeg_path, get_ffprobe_path


# Kalite etiketleri — çözünürlüğe göre
QUALITY_LABELS = {
    2160: "4K",
    1440: "1440p",
    1080: "1080p",
    720: "720p",
    480: "480p",
    360: "360p",
    240: "240p",
    144: "144p",
}


def _detect_platform(url: str) -> str:
    """URL'den platform adını çıkarır."""
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    if "instagram.com" in url_lower:
        return "instagram"
    if "tiktok.com" in url_lower:
        return "tiktok"
    if "twitter.com" in url_lower or "x.com" in url_lower:
        return "twitter"
    if "facebook.com" in url_lower or "fb.watch" in url_lower:
        return "facebook"
    return "unknown"


def _get_quality_label(height: int | None) -> str:
    """Piksel yüksekliğinden kalite etiketi üretir."""
    if height is None:
        return "Bilinmeyen"
    for h, label in QUALITY_LABELS.items():
        if height >= h:
            return label
    return f"{height}p"


def _format_filesize(size_bytes: int | None) -> str | None:
    """Bayt cinsinden dosya boyutunu okunabilir hale getirir."""
    if size_bytes is None:
        return None
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def _parse_formats(raw_formats: list[dict]) -> list[dict]:
    """Ham yt-dlp format listesini temizler ve gruplar."""
    seen_heights: set[int] = set()
    result = []

    # Yüksek kaliteden (height ve tbr) düşüğe sırala
    sorted_formats = sorted(
        raw_formats,
        key=lambda f: (f.get("height") or 0, f.get("tbr") or 0),
        reverse=True,
    )

    for fmt in sorted_formats:
        vcodec = fmt.get("vcodec", "none")
        acodec = fmt.get("acodec", "none")
        ext = fmt.get("ext", "")
        height = fmt.get("height")
        fps = fmt.get("fps")

        # Sadece ses formatları
        is_audio_only = (vcodec == "none" or not vcodec) and acodec not in ("none", None)

        if is_audio_only:
            continue

        # Yalnızca görüntü (ses yok) — FFmpeg ile birleştirmek için kullanılır
        is_video_only = (acodec == "none" or not acodec)

        # Eğer height None ise veya 0 ise geç
        if not height:
            continue

        # Her çözünürlükten (height) sadece en iyi kaliteye sahip olanı al
        if height in seen_heights:
            continue
        seen_heights.add(height)

        quality_label = _get_quality_label(height)
        filesize = fmt.get("filesize") or fmt.get("filesize_approx")

        result.append({
            "format_id": fmt.get("format_id", ""),
            "ext": ext,
            "quality_label": quality_label,
            "width": fmt.get("width"),
            "height": height,
            "resolution": f"{fmt.get('width', '?')}x{height}" if height else None,
            "fps": int(fps) if fps else None,
            "vcodec": vcodec,
            "acodec": acodec,
            "tbr": fmt.get("tbr"),
            "filesize": filesize,
            "filesize_str": _format_filesize(filesize),
            "is_audio_only": False,
            "is_video_only": is_video_only,
        })

    return result


def analyze_url(url: str, timeout: int = 30) -> dict[str, Any]:
    """
    URL'yi analiz eder ve meta veri + format listesini döndürür.

    Args:
        url: YouTube/Instagram/TikTok video veya playlist URL'si
        timeout: Maksimum bekleme süresi (saniye)

    Returns:
        Video bilgileri ve format listesi içeren sözlük

    Raises:
        ValueError: Geçersiz URL veya desteklenmeyen platform
        PermissionError: Private/kısıtlı video
        ConnectionError: Ağ bağlantısı hatası
        RuntimeError: Diğer yt-dlp hataları
    """
    platform = _detect_platform(url)

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "ffmpeg_location": get_ffmpeg_path(),
        "socket_timeout": timeout,
        "retries": 3,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.ExtractorError as e:
        err_msg = str(e).lower()
        if "private" in err_msg or "login" in err_msg or "age" in err_msg:
            raise PermissionError(
                "Bu video özel veya kısıtlıdır. Giriş yapmanız gerekebilir."
            )
        if "not available" in err_msg or "removed" in err_msg:
            raise ValueError("Video mevcut değil veya kaldırılmış.")
        raise ValueError(f"Video analiz edilemedi: {e}")
    except yt_dlp.utils.DownloadError as e:
        err_msg = str(e).lower()
        if "network" in err_msg or "connection" in err_msg or "timeout" in err_msg:
            raise ConnectionError("İnternet bağlantısı hatası. Bağlantınızı kontrol edin.")
        raise RuntimeError(f"İndirme hatası: {e}")
    except Exception as e:
        raise RuntimeError(f"Beklenmeyen hata: {e}")

    if info is None:
        raise ValueError("Video bilgisi alınamadı.")

    # Playlist mi?
    is_playlist = info.get("_type") == "playlist" or "entries" in info
    entries = []
    if is_playlist:
        entries = [
            {
                "id": e.get("id", ""),
                "title": e.get("title", "Bilinmeyen"),
                "url": e.get("url") or e.get("webpage_url", ""),
                "duration": e.get("duration"),
                "thumbnail": e.get("thumbnail"),
            }
            for e in (info.get("entries") or [])
            if e
        ]
        # Playlist özeti için ilk entry'den format al
        formats = []
    else:
        raw_formats = info.get("formats") or []
        formats = _parse_formats(raw_formats)

    return {
        "title": info.get("title") or info.get("id", "Bilinmeyen"),
        "uploader": info.get("uploader") or info.get("channel") or "",
        "duration": info.get("duration"),
        "thumbnail": info.get("thumbnail"),
        "platform": platform,
        "url": url,
        "is_playlist": is_playlist,
        "playlist_count": len(entries) if is_playlist else None,
        "formats": formats,
        "entries": entries,
        # Raw info for downloader use
        "_webpage_url": info.get("webpage_url") or url,
        "_id": info.get("id", ""),
    }