"""
history_db.py
-------------
SQLite tabanlı indirme geçmişi veritabanı katmanı.
Kayıtları %APPDATA%/VideoConverter/history.db (veya diğer OS'lerde .config/VideoConverter/history.db) altında saklar.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def get_db_path() -> str:
    """Veritabanı dosyasının yolunu döndürür, dizinini otomatik oluşturur."""
    if sys.platform == "win32":
        base_dir = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    else:
        base_dir = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")

    db_dir = os.path.join(base_dir, "VideoConverter")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, "history.db")


def init_db():
    """Veritabanını ve gerekli tabloları başlatır."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            title TEXT NOT NULL,
            thumbnail_url TEXT,
            format_type TEXT NOT NULL, -- 'mp4' | 'mp3'
            quality TEXT,              -- '1080p', '320 kbps' vb.
            download_date TEXT NOT NULL,
            file_path TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def add_record(
    url: str,
    title: str,
    thumbnail_url: str | None,
    format_type: str,
    quality: str | None,
    file_path: str,
) -> int:
    """Yeni bir indirme kaydı ekler. Eklenen kaydın ID'sini döner."""
    init_db()  # Tablo yoksa oluşturulduğundan emin ol
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    download_date = datetime.now().isoformat()
    cursor.execute(
        """
        INSERT INTO history (url, title, thumbnail_url, format_type, quality, download_date, file_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (url, title, thumbnail_url or "", format_type, quality or "best", download_date, file_path),
    )
    new_id = cursor.lastrowid or 0
    conn.commit()
    conn.close()
    return new_id


def get_records(search_query: str | None = None) -> list[dict[str, Any]]:
    """Geçmişteki tüm kayıtları (tarihe göre azalan) veya arama kriterine uyanları döndürür."""
    init_db()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    # Satırları dictionary olarak döndürmek için row_factory ayarlıyoruz
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if search_query:
        cursor.execute(
            """
            SELECT * FROM history
            WHERE title LIKE ? OR url LIKE ?
            ORDER BY download_date DESC
            """,
            (f"%{search_query}%", f"%{search_query}%"),
        )
    else:
        cursor.execute("SELECT * FROM history ORDER BY download_date DESC")

    rows = cursor.fetchall()
    result = [dict(row) for row in rows]
    conn.close()
    return result


def get_record_by_url(url: str) -> dict[str, Any] | None:
    """Verilen URL'e ait en son indirme kaydını döner."""
    init_db()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT * FROM history
        WHERE url = ?
        ORDER BY download_date DESC
        LIMIT 1
        """,
        (url,),
    )
    row = cursor.fetchone()
    result = dict(row) if row else None
    conn.close()
    return result


def delete_record(record_id: int):
    """Kaydı veritabanından siler."""
    init_db()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM history WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()


def clear_history():
    """Tüm geçmişi temizler."""
    init_db()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM history")
    conn.commit()
    conn.close()
