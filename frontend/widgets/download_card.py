"""
download_card.py
----------------
Tek bir indirme görevini gösteren kart widget'ı.
Progress bar, başlık, platform, hız, ETA ve iptal butonu içerir.
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QProgressBar, QSizePolicy,
)

from backend.downloader import DownloadTask, DownloadWorker, DownloadStatus


PLATFORM_EMOJIS = {
    "youtube":   "▶",
    "instagram": "📸",
    "tiktok":    "🎵",
    "twitter":   "🐦",
    "facebook":  "👤",
    "unknown":   "🌐",
}

STATUS_COLORS = {
    "downloading": "#e94560",
    "converting":  "#7c5cbf",
    "finished":    "#4ade80",
    "error":       "#f87171",
    "cancelled":   "#606070",
    "pending":     "#a0a0b0",
}


class DownloadCard(QFrame):
    """
    İndirme kuyruğundaki her iş için gösterilen kart.

    ┌──────────────────────────────────────────────────────────┐
    │ ▶  [Platform]   Başlık / başlık...            [✕ İptal] │
    │    ████████████░░░░░░░░░░░░░░░ 42%   2.3 MB/s  01:23    │
    │    Durum metni                                           │
    └──────────────────────────────────────────────────────────┘
    """

    cancel_requested = pyqtSignal(str)   # task_id
    open_folder_requested = pyqtSignal(str)  # klasör yolu

    def __init__(self, task: DownloadTask, parent=None):
        super().__init__(parent)
        self.task = task
        self._worker: DownloadWorker | None = None
        self._output_path: str = task.output_dir
        self._status = DownloadStatus.PENDING

        self.setProperty("class", "card")
        self.setFixedHeight(92)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._build_ui()

    def _build_ui(self):
        main = QHBoxLayout(self)
        main.setContentsMargins(16, 12, 16, 12)
        main.setSpacing(12)

        # Platform emoji
        platform_icon = PLATFORM_EMOJIS.get(self.task.platform, "🌐")
        icon_lbl = QLabel(platform_icon)
        icon_lbl.setFixedWidth(22)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        icon_lbl.setStyleSheet("font-size: 18px;")

        # İçerik kolonu
        content = QVBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(5)

        # Başlık satırı
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)

        title = self.task.title or self.task.url
        self._title_lbl = QLabel(title[:65] + ("..." if len(title) > 65 else ""))
        self._title_lbl.setStyleSheet("font-weight: 600; font-size: 13px;")
        self._title_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        fmt_badge = QLabel(self.task.format_type.upper())
        fmt_badge.setStyleSheet(
            "background:#e94560; color:#fff; border-radius:4px; "
            "padding:1px 6px; font-size:10px; font-weight:700;"
        )
        fmt_badge.setFixedHeight(18)

        title_row.addWidget(self._title_lbl, 1)
        title_row.addWidget(fmt_badge)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(6)
        self._progress_bar.setTextVisible(False)

        # Alt bilgi satırı
        info_row = QHBoxLayout()
        info_row.setContentsMargins(0, 0, 0, 0)
        info_row.setSpacing(12)

        self._status_lbl = QLabel("Bekliyor...")
        self._status_lbl.setProperty("class", "muted")
        self._status_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._percent_lbl = QLabel("0%")
        self._percent_lbl.setProperty("class", "muted")
        self._percent_lbl.setFixedWidth(32)
        self._percent_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)

        self._speed_lbl = QLabel("—")
        self._speed_lbl.setProperty("class", "speed")
        self._speed_lbl.setFixedWidth(70)
        self._speed_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)

        self._eta_lbl = QLabel("—")
        self._eta_lbl.setProperty("class", "speed")
        self._eta_lbl.setFixedWidth(45)
        self._eta_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)

        info_row.addWidget(self._status_lbl, 1)
        info_row.addWidget(self._percent_lbl)
        info_row.addWidget(self._speed_lbl)
        info_row.addWidget(self._eta_lbl)

        content.addLayout(title_row)
        content.addWidget(self._progress_bar)
        content.addLayout(info_row)

        # Butonlar kolonu
        btn_col = QVBoxLayout()
        btn_col.setContentsMargins(0, 0, 0, 0)
        btn_col.setSpacing(4)
        btn_col.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._cancel_btn = QPushButton("✕")
        self._cancel_btn.setProperty("class", "ghost")
        self._cancel_btn.setFixedSize(28, 28)
        self._cancel_btn.setToolTip("İptal et")
        self._cancel_btn.clicked.connect(self._on_cancel)

        self._open_btn = QPushButton("📁")
        self._open_btn.setProperty("class", "ghost")
        self._open_btn.setFixedSize(28, 28)
        self._open_btn.setToolTip("Klasörü aç")
        self._open_btn.setVisible(False)
        self._open_btn.clicked.connect(self._on_open_folder)

        btn_col.addWidget(self._cancel_btn)
        btn_col.addWidget(self._open_btn)

        main.addWidget(icon_lbl)
        main.addLayout(content, 1)
        main.addLayout(btn_col)

    def attach_worker(self, worker: DownloadWorker):
        """Worker sinyallerini bu karta bağlar."""
        self._worker = worker
        worker.progress.connect(self._on_progress)
        worker.speed.connect(self._speed_lbl.setText)
        worker.eta.connect(self._eta_lbl.setText)
        worker.status.connect(self._on_status)
        worker.finished.connect(self._on_finished)
        worker.error.connect(self._on_error)
        worker.title_found.connect(self._on_title_found)

    def _on_progress(self, pct: int):
        self._progress_bar.setValue(pct)
        self._percent_lbl.setText(f"{pct}%")

    def _on_status(self, msg: str):
        self._status_lbl.setText(msg)

    def _on_title_found(self, title: str):
        if title:
            self.task.title = title
            self._title_lbl.setText(title[:65] + ("..." if len(title) > 65 else ""))

    def _on_finished(self, path: str):
        self._output_path = path
        self._status = DownloadStatus.FINISHED
        self._progress_bar.setValue(100)
        self._percent_lbl.setText("100%")
        self._speed_lbl.setText("✓")
        self._eta_lbl.setText("")
        self._status_lbl.setText("Tamamlandı!")
        self._status_lbl.setStyleSheet("color: #4ade80; font-size: 12px;")
        self._cancel_btn.setVisible(False)
        self._open_btn.setVisible(True)
        # Progress bar yeşile dön
        self._progress_bar.setStyleSheet(
            "QProgressBar::chunk { background: #4ade80; border-radius: 4px; }"
        )

    def _on_error(self, msg: str):
        self._status = DownloadStatus.ERROR
        self._status_lbl.setText(f"Hata: {msg[:80]}")
        self._status_lbl.setStyleSheet("color: #f87171; font-size: 11px;")
        self._speed_lbl.setText("")
        self._eta_lbl.setText("")
        self._cancel_btn.setVisible(False)
        self._progress_bar.setStyleSheet(
            "QProgressBar::chunk { background: #f87171; border-radius: 4px; }"
        )

    def _on_cancel(self):
        if self._worker:
            self._worker.cancel()
        self._status = DownloadStatus.CANCELLED
        self._status_lbl.setText("İptal edildi")
        self._status_lbl.setStyleSheet("color: #606070; font-size: 12px;")
        self._cancel_btn.setVisible(False)
        self.cancel_requested.emit(self.task.task_id)

    def _on_open_folder(self):
        folder = os.path.dirname(self._output_path) if os.path.isfile(self._output_path) else self._output_path
        self.open_folder_requested.emit(folder)

    def set_pending(self):
        """Kuyrukta bekliyor durumu."""
        self._status_lbl.setText("Kuyrukta bekliyor...")
        self._status_lbl.setStyleSheet("")

    def get_status(self) -> DownloadStatus:
        return self._status
