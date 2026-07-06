"""
history_panel.py
----------------
Geçmiş sekmesini ve geçmişteki her indirmeyi gösteren kartları içerir.
Arama filtreleme, klasör açma, tekrar indirme ve geçmişten silme işlemlerini yönetir.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import sys
import requests
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QLabel, QPushButton, QScrollArea, QFrame,
    QSizePolicy, QMessageBox,
)

def get_icon_path(filename: str) -> str:
    """Proje assets/icons klasöründen veya paketlenmiş _MEIPASS dizininden ikon yolunu çeker."""
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    return os.path.abspath(os.path.join(base_dir, "assets", "icons", filename))


from backend import history_db


class ImageLoader(QThread):
    """Görselleri arka planda yükleyerek UI'ı kilitlemez."""
    loaded = pyqtSignal(bytes)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            # Sadece HTTP/HTTPS linkleri için
            if self.url.startswith("http"):
                res = requests.get(self.url, timeout=5)
                if res.status_code == 200:
                    self.loaded.emit(res.content)
        except Exception:
            pass


class HistoryCard(QFrame):
    """
    Geçmiş listesindeki her bir indirme kaydını temsil eden kart.
    """

    redownload_requested = pyqtSignal(str)   # url
    delete_requested = pyqtSignal(int)       # record_id
    open_folder_requested = pyqtSignal(str)  # file_path

    def __init__(self, record: dict[str, Any], parent=None):
        super().__init__(parent)
        self.record = record
        self._image_loader: ImageLoader | None = None

        self.setProperty("class", "item-card")
        self.setFixedHeight(84)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._build_ui()
        self._load_thumbnail()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # Görsel Alanı (Thumbnail veya Platform İkonu)
        self._img_lbl = QLabel()
        self._img_lbl.setFixedSize(96, 54)
        self._img_lbl.setProperty("class", "thumbnail")
        self._img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_default_platform_icon()
        layout.addWidget(self._img_lbl)

        # Bilgi alanı (Dikey)
        info = QVBoxLayout()
        info.setContentsMargins(0, 2, 0, 2)
        info.setSpacing(4)

        # Başlık ve Platform/Format Badgeleri
        meta_row = QHBoxLayout()
        meta_row.setSpacing(8)

        title = self.record.get("title", "Bilinmeyen Video")
        self._title_lbl = QLabel(title[:60] + ("..." if len(title) > 60 else ""))
        self._title_lbl.setStyleSheet("font-weight: 600; font-size: 13px;")
        self._title_lbl.setToolTip(title)

        fmt = self.record.get("format_type", "mp4").upper()
        fmt_badge = QLabel(fmt)
        badge_color = "#e94560" if fmt == "MP4" else "#7c5cbf"
        fmt_badge.setStyleSheet(
            f"background: {badge_color}; color: #fff; border-radius: 4px; "
            "padding: 1px 6px; font-size: 7pt; font-weight: 700;"
        )
        fmt_badge.setFixedHeight(16)

        quality = self.record.get("quality") or ""
        quality_badge = QLabel(quality)
        quality_badge.setStyleSheet(
            "background: #2a2a3a; color: #a0a0b0; border-radius: 4px; "
            "padding: 1px 6px; font-size: 7pt; font-weight: 600;"
        )
        quality_badge.setFixedHeight(16)
        if not quality:
            quality_badge.setVisible(False)

        meta_row.addWidget(self._title_lbl, 1)
        meta_row.addWidget(quality_badge)
        meta_row.addWidget(fmt_badge)
        info.addLayout(meta_row)

        # Tarih ve dosya durumu satırı
        details_row = QHBoxLayout()
        details_row.setSpacing(12)

        # ISO tarihi formatla
        date_str = self.record.get("download_date", "")
        formatted_date = ""
        try:
            dt = datetime.fromisoformat(date_str)
            formatted_date = dt.strftime("%d.%m.%Y %H:%M")
        except ValueError:
            formatted_date = date_str

        date_lbl = QLabel(formatted_date)
        date_lbl.setProperty("class", "muted")
        date_lbl.setStyleSheet("font-size: 8.5pt;")

        # Dosya diske duruyor mu?
        self._path = self.record.get("file_path", "")
        file_exists = os.path.exists(self._path)
        self._status_lbl = QLabel("✓ Kayıtlı" if file_exists else "⚠ Dosya silinmiş")
        self._status_lbl.setStyleSheet(
            "color: #00e676; font-size: 8.5pt; font-weight: 600;" if file_exists else "color: #ff1744; font-size: 8.5pt; font-weight: 600;"
        )

        details_row.addWidget(date_lbl)
        details_row.addWidget(self._status_lbl)
        details_row.addStretch()
        info.addLayout(details_row)

        layout.addLayout(info, 1)

        # Butonlar satırı (Sağ taraf)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        self._folder_btn = QPushButton("Klasörü Aç")
        self._folder_btn.setProperty("class", "secondary")
        self._folder_btn.setFixedHeight(30)
        self._folder_btn.clicked.connect(self._on_open_folder)
        # Dosya yoksa klasörü açmayı engelle
        self._folder_btn.setEnabled(file_exists)

        self._redownload_btn = QPushButton("Tekrar İndir")
        self._redownload_btn.setProperty("class", "secondary")
        self._redownload_btn.setFixedHeight(30)
        self._redownload_btn.clicked.connect(self._on_redownload)

        self._delete_btn = QPushButton("Sil")
        self._delete_btn.setProperty("class", "danger")
        self._delete_btn.setFixedHeight(30)
        self._delete_btn.clicked.connect(self._on_delete)

        btn_layout.addWidget(self._folder_btn)
        btn_layout.addWidget(self._redownload_btn)
        btn_layout.addWidget(self._delete_btn)
        layout.addLayout(btn_layout)

    def _set_default_platform_icon(self):
        """Thumbnail yüklenene kadar veya hata durumunda platform emojisini gösterir."""
        url = self.record.get("url", "").lower()
        if "youtube.com" in url or "youtu.be" in url:
            self._img_lbl.setText("▶")
            self._img_lbl.setStyleSheet("font-size: 15pt; color: #ff0000;")
        elif "instagram.com" in url:
            self._img_lbl.setText("📸")
            self._img_lbl.setStyleSheet("font-size: 15pt; color: #e1306c;")
        elif "tiktok.com" in url:
            self._img_lbl.setText("🎵")
            self._img_lbl.setStyleSheet("font-size: 15pt; color: #69c9d0;")
        else:
            self._img_lbl.setText("🌐")
            self._img_lbl.setStyleSheet("font-size: 15pt; color: #a0a0b0;")

    def update_theme(self, theme: str):
        suffix = "white" if theme == "dark" else "dark"
        
        folder_path = get_icon_path(f"folder_{suffix}.png")
        if os.path.isfile(folder_path):
            self._folder_btn.setIcon(QIcon(folder_path))
            self._folder_btn.setIconSize(QSize(14, 14))
            
        redownload_path = get_icon_path(f"download_tab_{suffix}.png")
        if os.path.isfile(redownload_path):
            self._redownload_btn.setIcon(QIcon(redownload_path))
            self._redownload_btn.setIconSize(QSize(14, 14))
            
        delete_path = get_icon_path(f"trash_{suffix}.png")
        if os.path.isfile(delete_path):
            self._delete_btn.setIcon(QIcon(delete_path))
            self._delete_btn.setIconSize(QSize(14, 14))

    def _load_thumbnail(self):
        url = self.record.get("thumbnail_url")
        if url:
            self._image_loader = ImageLoader(url)
            self._image_loader.loaded.connect(self._on_image_loaded)
            self._image_loader.start()

    def _on_image_loaded(self, data: bytes):
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            # En-boy oranını bozmadan sığdır
            scaled = pixmap.scaled(
                self._img_lbl.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            self._img_lbl.setPixmap(scaled)

    def _on_open_folder(self):
        self.open_folder_requested.emit(self._path)

    def _on_redownload(self):
        self.redownload_requested.emit(self.record.get("url", ""))

    def _on_delete(self):
        reply = QMessageBox.question(
            self,
            "Geçmişten Sil",
            "Bu kaydı geçmişten silmek istediğinize emin misiniz?\n(Disk üzerindeki dosya silinmeyecektir.)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.delete_requested.emit(self.record.get("id", 0))


class HistoryPanelWidget(QWidget):
    """
    Geçmiş sekmesinin ana paneli.
    Arama filtresini ve geçmiş kartlarının listesini barındırır.
    """

    redownload_requested = pyqtSignal(str)
    open_folder_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: list[HistoryCard] = []
        self._theme = "dark"
        self._build_ui()
        self.refresh_list()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Arama çubuğu ve filtreler alanı
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Geçmişte ara (Video adı veya link)...")
        self._search_input.setMinimumHeight(38)
        self._search_input.textChanged.connect(self._on_search_changed)
        
        self._search_action = self._search_input.addAction(
            QIcon(), QLineEdit.ActionPosition.LeadingPosition
        )

        self._clear_btn = QPushButton("Tümünü Temizle")
        self._clear_btn.setProperty("class", "ghost")
        self._clear_btn.setFixedHeight(38)
        self._clear_btn.clicked.connect(self._clear_all_history)

        filter_row.addWidget(self._search_input, 1)
        filter_row.addWidget(self._clear_btn)
        layout.addLayout(filter_row)

        # Scroll Area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(8)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Boş geçmiş uyarısı
        self._empty_label = QLabel("Henüz indirme geçmişi bulunmuyor.")
        self._empty_label.setProperty("class", "muted")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet("font-size: 10.5pt; margin-top: 50px;")
        self._list_layout.addWidget(self._empty_label)

        self._scroll.setWidget(self._list_container)
        layout.addWidget(self._scroll, 1)

    def refresh_list(self, query: str | None = None):
        """Veritabanındaki kayıtları çekip listeyi günceller."""
        # Eski kartları temizle
        for card in self._cards:
            card.setParent(None)
            card.deleteLater()
        self._cards.clear()

        # Kayıtları getir
        records = history_db.get_records(query)

        if not records:
            self._empty_label.setVisible(True)
            self._empty_label.setText(
                "Arama kriterlerine uygun geçmiş kaydı bulunamadı."
                if query else "Henüz indirme geçmişi bulunmuyor."
            )
        else:
            self._empty_label.setVisible(False)

            for rec in records:
                card = HistoryCard(rec, self)
                card.update_theme(self._theme)
                card.redownload_requested.connect(self.redownload_requested.emit)
                card.open_folder_requested.connect(self.open_folder_requested.emit)
                card.delete_requested.connect(self._delete_record)

                self._list_layout.addWidget(card)
                self._cards.append(card)

    def _on_search_changed(self, text: str):
        query = text.strip()
        self.refresh_list(query if query else None)

    def _delete_record(self, record_id: int):
        history_db.delete_record(record_id)
        # Listeyi mevcut arama terimine göre yenile
        self._on_search_changed(self._search_input.text())

    def _clear_all_history(self):
        records = history_db.get_records()
        if not records:
            return

        reply = QMessageBox.question(
            self,
            "Tüm Geçmişi Temizle",
            "Tüm indirme geçmişini silmek istediğinize emin misiniz?\n(Disk üzerindeki dosyalar silinmeyecektir!)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            history_db.clear_history()
            self._search_input.clear()
            self.refresh_list()

    def update_theme(self, theme: str):
        self._theme = theme
        suffix = "white" if theme == "dark" else "dark"
        
        search_icon_path = get_icon_path(f"search_{suffix}.png")
        if os.path.isfile(search_icon_path):
            self._search_action.setIcon(QIcon(search_icon_path))
            
        for card in self._cards:
            card.update_theme(theme)
