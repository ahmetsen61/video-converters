"""
url_input.py
------------
URL giriş widget'ı. Kullanıcı video URL'si girer ve "Analiz Et" butonuna basar.
Analiz sırasında spinner gösterir, analiz bittikten sonra QualitySelector açılır.

Sinyaller:
    analysis_done(dict)   - Başarılı analiz sonucu
    analysis_error(str)   - Hata mesajı
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QClipboard, QKeySequence, QIcon
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QLineEdit, QPushButton, QLabel, QFrame,
    QApplication, QSizePolicy,
)

import yt_dlp
from backend.analyzer import analyze_url


class AnalyzeWorker(QThread):
    """URL analizini arka planda yapar."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            result = analyze_url(self.url)
            self.finished.emit(result)
        except PermissionError as e:
            self.error.emit(str(e))
        except ValueError as e:
            self.error.emit(str(e))
        except ConnectionError as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(f"Beklenmeyen hata: {str(e)[:200]}")


class URLInputWidget(QWidget):
    """
    Ana URL giriş paneli.

    ┌─────────────────────────────────────────────────────────────┐
    │  [Paste] [                URL girin...              ] [Analiz Et] │
    └─────────────────────────────────────────────────────────────┘
    │ Durum mesajı / hata                                         │
    """

    analysis_done = pyqtSignal(dict)
    analysis_error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: AnalyzeWorker | None = None
        self._dot_count = 0
        self._timer = QTimer()
        self._timer.timeout.connect(self._animate_dots)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ---- Ana giriş satırı ----
        input_frame = QFrame()
        input_frame.setProperty("class", "card")
        input_frame.setFixedHeight(64)
        row = QHBoxLayout(input_frame)
        row.setContentsMargins(8, 8, 8, 8)
        row.setSpacing(8)

        # Yapıştır butonu
        self._paste_btn = QPushButton()
        self._paste_btn.setProperty("class", "secondary")
        self._paste_btn.setToolTip("Panodan yapıştır (Ctrl+V)")
        self._paste_btn.setFixedSize(40, 40)
        self._paste_btn.clicked.connect(self._paste_from_clipboard)

        # URL giriş alanı
        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText(
            "YouTube, Instagram veya TikTok video linkini buraya yapıştırın..."
        )
        self._url_input.setMinimumHeight(40)
        self._url_input.returnPressed.connect(self._on_analyze)
        self._url_input.textChanged.connect(self._on_text_changed)

        # Temizle butonu (URL varsa göster)
        self._clear_btn = QPushButton()
        self._clear_btn.setProperty("class", "ghost")
        self._clear_btn.setFixedSize(32, 32)
        self._clear_btn.setVisible(False)
        self._clear_btn.clicked.connect(self._clear)

        # Analiz Et butonu
        self._analyze_btn = QPushButton("Analiz Et")
        self._analyze_btn.setFixedHeight(40)
        self._analyze_btn.setMinimumWidth(110)
        self._analyze_btn.clicked.connect(self._on_analyze)

        row.addWidget(self._paste_btn)
        row.addWidget(self._url_input, 1)
        row.addWidget(self._clear_btn)
        row.addWidget(self._analyze_btn)

        # ---- Durum satırı ----
        self._status_label = QLabel("")
        self._status_label.setProperty("class", "muted")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(input_frame)
        layout.addWidget(self._status_label)

    def _on_text_changed(self, text: str):
        self._clear_btn.setVisible(bool(text))
        self._status_label.setText("")

    def _paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if text:
            self._url_input.setText(text)
            self._url_input.setFocus()

    def _clear(self):
        self._url_input.clear()
        self._status_label.setText("")
        self._status_label.setProperty("class", "muted")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

    def _on_analyze(self):
        url = self._url_input.text().strip()
        if not url:
            self._show_error("Lütfen bir video linki girin.")
            return

        if not (url.startswith("http://") or url.startswith("https://")):
            self._show_error("Geçersiz URL. http:// veya https:// ile başlamalı.")
            return

        self._set_analyzing(True)
        self._worker = AnalyzeWorker(url)
        self._worker.finished.connect(self._on_analysis_done)
        self._worker.error.connect(self._on_analysis_error)
        self._worker.start()

    def _on_analysis_done(self, result: dict):
        self._set_analyzing(False)
        title = result.get("title", "Video")
        self._status_label.setText(f"✓ Bulundu: {title[:60]}")
        self._status_label.setProperty("class", "success")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)
        self.analysis_done.emit(result)

    def _on_analysis_error(self, error_msg: str):
        self._set_analyzing(False)
        self._show_error(error_msg)
        self.analysis_error.emit(error_msg)

    def _show_error(self, msg: str):
        self._status_label.setText(f"✗ {msg}")
        self._status_label.setProperty("class", "error")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

    def _set_analyzing(self, analyzing: bool):
        self._analyze_btn.setEnabled(not analyzing)
        self._url_input.setEnabled(not analyzing)
        self._paste_btn.setEnabled(not analyzing)
        if analyzing:
            self._dot_count = 0
            self._timer.start(400)
            self._status_label.setText("Analiz ediliyor...")
            self._status_label.setProperty("class", "muted")
            self._status_label.style().unpolish(self._status_label)
            self._status_label.style().polish(self._status_label)
        else:
            self._timer.stop()
            self._analyze_btn.setText("Analiz Et")

    def _animate_dots(self):
        self._dot_count = (self._dot_count + 1) % 4
        dots = "." * self._dot_count
        self._status_label.setText(f"Analiz ediliyor{dots}")

    def set_url(self, url: str):
        """Programatik olarak URL ayarlar."""
        self._url_input.setText(url)

    def get_url(self) -> str:
        return self._url_input.text().strip()

    def update_theme(self, theme: str):
        import sys, os
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        suffix = "white" if theme == "dark" else "dark"
        
        paste_path = os.path.join(base_dir, "assets", "icons", f"paste_{suffix}.png")
        if os.path.isfile(paste_path):
            self._paste_btn.setIcon(QIcon(paste_path))
            self._paste_btn.setIconSize(QSize(16, 16))
            
        trash_path = os.path.join(base_dir, "assets", "icons", f"trash_{suffix}.png")
        if os.path.isfile(trash_path):
            self._clear_btn.setIcon(QIcon(trash_path))
            self._clear_btn.setIconSize(QSize(14, 14))
