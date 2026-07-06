"""
quality_selector.py
-------------------
Format ve kalite seçim dialog'u. Analiz sonrası açılır.
Kullanıcı MP4/MP3, kalite ve indirme klasörünü seçer.

Sinyaller:
    download_requested(DownloadTask) - İndirme isteği
"""

from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QFrame, QFileDialog,
    QLineEdit, QButtonGroup, QAbstractButton, QScrollArea,
    QWidget, QCheckBox, QSizePolicy,
)

from backend.downloader import DownloadTask


PLATFORM_ICONS = {
    "youtube": "▶ YouTube",
    "instagram": "📸 Instagram",
    "tiktok": "🎵 TikTok",
    "twitter": "🐦 Twitter",
    "facebook": "👤 Facebook",
    "unknown": "🌐 Web",
}

PLATFORM_CLASSES = {
    "youtube": "platform-youtube",
    "instagram": "platform-instagram",
    "tiktok": "platform-tiktok",
    "twitter": "platform-youtube",
    "facebook": "platform-instagram",
    "unknown": "muted",
}

MP3_QUALITIES = ["320 kbps", "256 kbps", "192 kbps", "128 kbps"]
MP3_BITRATES  = ["320", "256", "192", "128"]


class FormatToggle(QFrame):
    """MP4 / MP3 toggle buton grubu."""

    format_changed = pyqtSignal(str)  # "mp4" | "mp3"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current = "mp4"
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        self.setProperty("class", "card")
        self.setFixedHeight(48)

        self._mp4_btn = QPushButton("🎬  MP4 (Video)")
        self._mp4_btn.setCheckable(False)
        self._mp4_btn.setFixedHeight(36)
        self._mp4_btn.clicked.connect(lambda: self._select("mp4"))

        self._mp3_btn = QPushButton("🎵  MP3 (Ses)")
        self._mp3_btn.setCheckable(False)
        self._mp3_btn.setFixedHeight(36)
        self._mp3_btn.clicked.connect(lambda: self._select("mp3"))

        layout.addWidget(self._mp4_btn)
        layout.addWidget(self._mp3_btn)

        self._select("mp4")

    def _select(self, fmt: str):
        self._current = fmt
        # Aktif olan kırmızı, pasif secondary
        if fmt == "mp4":
            self._mp4_btn.setProperty("class", "")
            self._mp3_btn.setProperty("class", "secondary")
        else:
            self._mp4_btn.setProperty("class", "secondary")
            self._mp3_btn.setProperty("class", "")

        for btn in [self._mp4_btn, self._mp3_btn]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self.format_changed.emit(fmt)

    def get_format(self) -> str:
        return self._current


class QualitySelectorDialog(QDialog):
    """
    Video analizi tamamlandıktan sonra açılan kalite seçim dialog'u.

    Playlist ise liste gösterir, tek video ise direkt seçim yapar.
    """

    download_requested = pyqtSignal(list)  # list of DownloadTask

    def __init__(self, video_info: dict, default_dir: str, parent=None):
        super().__init__(parent)
        self._info = video_info
        self._default_dir = default_dir
        self._output_dir = default_dir
        self._selected_entries: list[dict] = []  # Playlist için

        self.setWindowTitle("İndirme Seçenekleri")
        self.setMinimumWidth(580)
        self.setMinimumHeight(400)
        self.setModal(True)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # ---- Başlık ----
        title_row = QHBoxLayout()
        platform = self._info.get("platform", "unknown")

        platform_lbl = QLabel(PLATFORM_ICONS.get(platform, "🌐"))
        platform_lbl.setProperty("class", PLATFORM_CLASSES.get(platform, "muted"))
        platform_lbl.setFixedWidth(90)

        title = self._info.get("title", "Video")
        title_lbl = QLabel(title[:70] + ("..." if len(title) > 70 else ""))
        title_lbl.setProperty("class", "subtitle")
        title_lbl.setWordWrap(True)
        title_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        title_row.addWidget(platform_lbl)
        title_row.addWidget(title_lbl, 1)
        layout.addLayout(title_row)

        sep = QFrame(); sep.setProperty("class", "separator"); sep.setFixedHeight(1)
        layout.addWidget(sep)

        # ---- Playlist ise ----
        if self._info.get("is_playlist"):
            self._build_playlist_section(layout)
        else:
            self._build_single_section(layout)

        # ---- Klasör seçimi ----
        layout.addWidget(self._build_folder_section())

        sep2 = QFrame(); sep2.setProperty("class", "separator"); sep2.setFixedHeight(1)
        layout.addWidget(sep2)

        # ---- Butonlar ----
        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("İptal")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.clicked.connect(self.reject)

        self._download_btn = QPushButton("⬇  İndir")
        self._download_btn.setMinimumWidth(140)
        self._download_btn.clicked.connect(self._on_download)

        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._download_btn)
        layout.addLayout(btn_row)

    # ---- Tek video seçim alanı ----
    def _build_single_section(self, layout: QVBoxLayout):
        formats = self._info.get("formats", [])

        # Format toggle
        self._format_toggle = FormatToggle()
        self._format_toggle.format_changed.connect(self._on_format_changed)
        layout.addWidget(self._format_toggle)

        # Kalite seçici
        quality_row = QHBoxLayout()
        quality_lbl = QLabel("Kalite:")
        quality_lbl.setFixedWidth(70)

        self._quality_combo = QComboBox()
        self._video_formats = formats
        self._populate_quality_combo("mp4")

        self._mp3_quality_combo = QComboBox()
        for q in MP3_QUALITIES:
            self._mp3_quality_combo.addItem(q)
        self._mp3_quality_combo.setVisible(False)

        quality_row.addWidget(quality_lbl)
        quality_row.addWidget(self._quality_combo, 1)
        quality_row.addWidget(self._mp3_quality_combo, 1)
        layout.addLayout(quality_row)

    def _populate_quality_combo(self, fmt: str):
        self._quality_combo.clear()
        if fmt == "mp4":
            if self._video_formats:
                for f in self._video_formats:
                    label = f.get("quality_label", "?")
                    fps = f.get("fps")
                    size = f.get("filesize_str", "")
                    fps_str = f" {fps}fps" if fps else ""
                    size_str = f" (~{size})" if size else ""
                    self._quality_combo.addItem(
                        f"{label}{fps_str}{size_str}",
                        userData=f
                    )
            else:
                self._quality_combo.addItem("En İyi Kalite", userData=None)
        else:
            self._quality_combo.addItem("En İyi Ses", userData=None)

    def _on_format_changed(self, fmt: str):
        is_mp4 = fmt == "mp4"
        self._quality_combo.setVisible(is_mp4)
        self._mp3_quality_combo.setVisible(not is_mp4)
        self._populate_quality_combo(fmt)

    # ---- Playlist seçim alanı ----
    def _build_playlist_section(self, layout: QVBoxLayout):
        entries = self._info.get("entries", [])
        count = self._info.get("playlist_count", len(entries))

        info_lbl = QLabel(f"Bu bir playlist ({count} video). Ne yapmak istersiniz?")
        info_lbl.setProperty("class", "subtitle")
        layout.addWidget(info_lbl)

        # Tümünü indir checkbox
        self._all_check = QCheckBox(f"Tüm playlist'i indir ({count} video)")
        self._all_check.setChecked(True)
        self._all_check.stateChanged.connect(self._on_all_toggled)
        layout.addWidget(self._all_check)

        # Format seçimi (playlist için de)
        self._format_toggle = FormatToggle()
        layout.addWidget(self._format_toggle)

        # MP3 kalite (playlist)
        mp3_row = QHBoxLayout()
        mp3_lbl = QLabel("Ses Kalitesi:")
        mp3_lbl.setFixedWidth(90)
        self._mp3_quality_combo = QComboBox()
        for q in MP3_QUALITIES:
            self._mp3_quality_combo.addItem(q)
        self._mp3_quality_combo.setVisible(False)
        mp3_row.addWidget(mp3_lbl)
        mp3_row.addWidget(self._mp3_quality_combo)
        mp3_row.addStretch()
        layout.addLayout(mp3_row)

        self._format_toggle.format_changed.connect(
            lambda f: self._mp3_quality_combo.setVisible(f == "mp3")
        )

        # Video listesi (seçim için)
        if entries:
            scroll = QScrollArea()
            scroll.setMaximumHeight(200)
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

            list_widget = QWidget()
            list_layout = QVBoxLayout(list_widget)
            list_layout.setContentsMargins(0, 0, 0, 0)
            list_layout.setSpacing(4)

            self._entry_checks: list[QCheckBox] = []
            for i, entry in enumerate(entries[:50]):  # Max 50 göster
                cb = QCheckBox(f"{i+1}. {entry.get('title', 'Video')[:60]}")
                cb.setChecked(True)
                cb.setEnabled(False)  # Başta "tümü" seçili, disable
                self._entry_checks.append(cb)
                list_layout.addWidget(cb)

            if len(entries) > 50:
                more_lbl = QLabel(f"... ve {len(entries) - 50} video daha")
                more_lbl.setProperty("class", "muted")
                list_layout.addWidget(more_lbl)

            list_layout.addStretch()
            scroll.setWidget(list_widget)
            layout.addWidget(scroll)

    def _on_all_toggled(self, state: int):
        checked = state == Qt.CheckState.Checked.value
        for cb in getattr(self, "_entry_checks", []):
            cb.setChecked(checked)
            cb.setEnabled(not checked)

    # ---- Klasör seçimi ----
    def _build_folder_section(self) -> QFrame:
        frame = QFrame()
        row = QHBoxLayout(frame)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        lbl = QLabel("Klasör:")
        lbl.setFixedWidth(70)

        self._folder_input = QLineEdit(self._output_dir)
        self._folder_input.setReadOnly(True)

        browse_btn = QPushButton("Gözat...")
        browse_btn.setProperty("class", "secondary")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._browse_folder)

        row.addWidget(lbl)
        row.addWidget(self._folder_input, 1)
        row.addWidget(browse_btn)
        return frame

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "İndirme Klasörü Seç", self._output_dir
        )
        if folder:
            self._output_dir = folder
            self._folder_input.setText(folder)

    # ---- İndirme başlatma ----
    def _on_download(self):
        info = self._info
        fmt = self._format_toggle.get_format()
        mp3_bitrate = "320"

        if fmt == "mp3":
            idx = self._mp3_quality_combo.currentIndex()
            mp3_bitrate = MP3_BITRATES[idx] if 0 <= idx < len(MP3_BITRATES) else "320"

        tasks = []

        if info.get("is_playlist"):
            entries = info.get("entries", [])
            all_checked = getattr(self, "_all_check", None) and self._all_check.isChecked()

            if all_checked:
                selected = entries
            else:
                selected = [
                    e for i, e in enumerate(entries)
                    if i < len(self._entry_checks) and self._entry_checks[i].isChecked()
                ]

            for entry in selected:
                task = DownloadTask(
                    url=entry.get("url") or entry.get("webpage_url", ""),
                    output_dir=self._output_dir,
                    format_type=fmt,
                    mp3_bitrate=mp3_bitrate,
                    title=entry.get("title", ""),
                    platform=info.get("platform", "unknown"),
                )
                tasks.append(task)
        else:
            # Tek video
            quality_height = None
            format_id = None
            selected_fmt = None

            if fmt == "mp4" and hasattr(self, "_quality_combo"):
                selected_fmt = self._quality_combo.currentData()
                if selected_fmt:
                    quality_height = selected_fmt.get("height") or selected_fmt.get("width")
                    format_id = selected_fmt.get("format_id")

            task = DownloadTask(
                url=info.get("_webpage_url") or info.get("url", ""),
                output_dir=self._output_dir,
                format_type=fmt,
                quality_height=quality_height,
                format_id=format_id,
                mp3_bitrate=mp3_bitrate,
                title=info.get("title", ""),
                thumbnail_url=info.get("thumbnail", ""),
                platform=info.get("platform", "unknown"),
            )
            tasks.append(task)

        if tasks:
            self.download_requested.emit(tasks)
            self.accept()
