"""
main_window.py
--------------
Ana uygulama penceresi. Tüm bileşenleri bir araya getirir.

Layout:
┌──────────────────────────────────────────────────────────┐
│ HEADER: Logo + Başlık + Tema toggle + Ayarlar            │
├──────────────────────────────────────────────────────────┤
│ URL INPUT: Link giriş alanı                              │
├──────────────────────────────────────────────────────────┤
│ DOWNLOAD QUEUE: İndirme kartları (scroll)                │
│                                                          │
│   [Boş durum: buraya link yapıştırın]                    │
│   [Kart 1] ████████░░░░ 65%  2.3 MB/s  00:45            │
│   [Kart 2] ░░░░░░░░░░░░  0%  Bekliyor...                 │
├──────────────────────────────────────────────────────────┤
│ STATUS BAR: X aktif, Y bekleyen, Z tamamlandı            │
└──────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QFont, QAction
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QFrame,
    QApplication, QStatusBar, QSizePolicy, QSpacerItem,
    QMessageBox, QTabWidget,
)

from backend.downloader import DownloadTask, DownloadWorker
from backend.queue_manager import QueueManager
from backend import history_db
from frontend.widgets.url_input import URLInputWidget
from frontend.widgets.quality_selector import QualitySelectorDialog
from frontend.widgets.download_card import DownloadCard
from frontend.widgets.settings_panel import SettingsDialog, load_settings
from frontend.widgets.history_panel import HistoryPanelWidget


def _load_stylesheet(theme: str) -> str:
    """QSS dosyasını yükler."""
    base = os.path.dirname(os.path.abspath(__file__))
    qss_path = os.path.join(base, "styles", f"{theme}_theme.qss")
    try:
        with open(qss_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


class EmptyStateWidget(QWidget):
    """İndirme kuyruğu boşken gösterilen widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        icon_lbl = QLabel("⬇")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 52px; color: #2a2a3a;")

        title_lbl = QLabel("Henüz indirme yok")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setProperty("class", "subtitle")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 600;")

        hint_lbl = QLabel("Yukarıya bir YouTube, Instagram veya TikTok linki yapıştırın.")
        hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_lbl.setProperty("class", "muted")

        layout.addWidget(icon_lbl)
        layout.addWidget(title_lbl)
        layout.addWidget(hint_lbl)


class MainWindow(QMainWindow):
    """Ana uygulama penceresi."""

    def __init__(self):
        super().__init__()
        self._settings = load_settings()
        self._cards: dict[str, DownloadCard] = {}  # task_id -> DownloadCard

        self._queue = QueueManager(
            max_concurrent=self._settings.get("max_concurrent", 3)
        )
        self._connect_queue_signals()

        self.setWindowTitle("VideoConverter")
        self.setMinimumSize(720, 580)
        self.resize(820, 660)

        # Pencere ikonu set et
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "assets", "app_icon.ico")
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Pencereyi ekran merkezine al
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                (geo.width() - 820) // 2,
                (geo.height() - 660) // 2,
            )

        # Veritabanını başlat
        history_db.init_db()

        self._build_ui()
        self._apply_theme(self._settings.get("theme", "dark"))

    # ================================================================
    # UI İnşası
    # ================================================================

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        root.addWidget(self._build_header())

        # Ana içerik
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 20, 24, 20)
        content_layout.setSpacing(20)

        # URL Giriş
        self._url_input = URLInputWidget()
        self._url_input.analysis_done.connect(self._on_analysis_done)
        self._url_input.analysis_error.connect(self._on_analysis_error)
        content_layout.addWidget(self._url_input)

        # İndirme Kuyruğu başlığı
        queue_header = QHBoxLayout()
        queue_lbl = QLabel("İndirme Kuyruğu")
        queue_lbl.setStyleSheet("font-size: 15px; font-weight: 700;")
        self._count_lbl = QLabel("")
        self._count_lbl.setProperty("class", "muted")
        clear_btn = QPushButton("Tümünü Temizle")
        clear_btn.setProperty("class", "ghost")
        clear_btn.setFixedHeight(28)
        clear_btn.clicked.connect(self._clear_completed)

        queue_header.addWidget(queue_lbl)
        queue_header.addWidget(self._count_lbl)
        queue_header.addStretch()
        queue_header.addWidget(clear_btn)
        content_layout.addLayout(queue_header)

        # Scroll area — download kartları
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._queue_container = QWidget()
        self._queue_layout = QVBoxLayout(self._queue_container)
        self._queue_layout.setContentsMargins(0, 0, 0, 0)
        self._queue_layout.setSpacing(8)
        self._queue_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Boş durum
        self._empty_state = EmptyStateWidget()
        self._queue_layout.addWidget(self._empty_state)

        self._scroll.setWidget(self._queue_container)
        content_layout.addWidget(self._scroll, 1)

        # Tab Widget
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("QTabWidget::pane { border: none; }")
        
        # Tab 1: İndir
        self._tabs.addTab(content, "⬇  İndir")
        
        # Tab 2: Geçmiş
        history_tab = QWidget()
        history_tab_layout = QVBoxLayout(history_tab)
        history_tab_layout.setContentsMargins(24, 20, 24, 20)
        history_tab_layout.setSpacing(20)
        
        self._history_panel = HistoryPanelWidget()
        self._history_panel.redownload_requested.connect(self._on_history_redownload)
        self._history_panel.open_folder_requested.connect(self._open_folder)
        
        history_tab_layout.addWidget(self._history_panel)
        self._tabs.addTab(history_tab, "📜  Geçmiş")
        
        # Sekme değişim sinyali
        self._tabs.currentChanged.connect(self._on_tab_changed)
        
        root.addWidget(self._tabs, 1)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._update_status()

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setProperty("class", "header")
        header.setFixedHeight(60)

        row = QHBoxLayout(header)
        row.setContentsMargins(20, 0, 20, 0)
        row.setSpacing(12)

        # Logo + Başlık
        logo_lbl = QLabel("🎬")
        logo_lbl.setStyleSheet("font-size: 24px;")
        logo_lbl.setFixedWidth(32)

        title_lbl = QLabel("VideoConverter")
        title_lbl.setStyleSheet("font-size: 17px; font-weight: 700;")

        version_lbl = QLabel("v1.0")
        version_lbl.setProperty("class", "muted")

        row.addWidget(logo_lbl)
        row.addWidget(title_lbl)
        row.addWidget(version_lbl)
        row.addStretch()

        # Platform destekleri
        for name, color in [("YouTube", "#ff0000"), ("Instagram", "#e1306c"), ("TikTok", "#69c9d0")]:
            lbl = QLabel(name)
            lbl.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 700;")
            row.addWidget(lbl)

        row.addSpacing(8)

        # Tema toggle
        self._theme_btn = QPushButton("☀")
        self._theme_btn.setProperty("class", "icon")
        self._theme_btn.setFixedSize(36, 36)
        self._theme_btn.setToolTip("Tema değiştir")
        self._theme_btn.clicked.connect(self._toggle_theme)
        row.addWidget(self._theme_btn)

        # Ayarlar
        settings_btn = QPushButton("⚙")
        settings_btn.setProperty("class", "icon")
        settings_btn.setFixedSize(36, 36)
        settings_btn.setToolTip("Ayarlar")
        settings_btn.clicked.connect(self._open_settings)
        row.addWidget(settings_btn)

        return header

    # ================================================================
    # Tema Yönetimi
    # ================================================================

    def _apply_theme(self, theme: str):
        self._settings["theme"] = theme
        stylesheet = _load_stylesheet(theme)
        QApplication.instance().setStyleSheet(stylesheet)
        self._theme_btn.setText("☀" if theme == "dark" else "🌙")

    def _toggle_theme(self):
        current = self._settings.get("theme", "dark")
        new_theme = "light" if current == "dark" else "dark"
        self._apply_theme(new_theme)

    # ================================================================
    # Analiz & İndirme
    # ================================================================

    def _on_analysis_done(self, video_info: dict):
        """URL analizi tamamlandı — kalite seçim dialog'unu aç (öncesinde mükerrer kontrolü yapar)."""
        from datetime import datetime
        url = video_info.get("url") or video_info.get("_webpage_url", "")
        
        # Geçmişte bu URL var mı bak
        record = history_db.get_record_by_url(url)
        if record:
            file_path = record.get("file_path", "")
            if os.path.exists(file_path):
                # Dosya diskte duruyor
                title = record.get("title", "Video")
                date_str = record.get("download_date", "")
                formatted_date = date_str
                try:
                    dt = datetime.fromisoformat(date_str)
                    formatted_date = dt.strftime("%d.%m.%Y %H:%M")
                except ValueError:
                    pass
                
                quality = record.get("quality", "Bilinmeyen")
                
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Zaten İndirildi")
                msg_box.setText(
                    f"Bu video daha önce indirilmiş.\n\n"
                    f"Başlık: {title}\n"
                    f"Tarih: {formatted_date}\n"
                    f"Kalite/Format: {quality}\n\n"
                    f"Tekrar indirmek yerine dosyayı açmak ister misiniz?"
                )
                open_btn = msg_box.addButton("Dosyayı Aç", QMessageBox.ButtonRole.YesRole)
                download_btn = msg_box.addButton("Yine de İndir", QMessageBox.ButtonRole.NoRole)
                cancel_btn = msg_box.addButton("İptal", QMessageBox.ButtonRole.RejectRole)
                msg_box.setDefaultButton(open_btn)
                
                msg_box.exec()
                
                clicked = msg_box.clickedButton()
                if clicked == open_btn:
                    self._open_folder(file_path)
                    return
                elif clicked == cancel_btn:
                    return
                # download_btn ise normal akışa devam eder
            else:
                # Dosya silinmiş
                self._status_bar.showMessage("Daha önce indirilmiş ama dosya bulunamadı, tekrar indirebilirsiniz.", 5000)

        # Normal kalite seçim diyalog akışı
        default_dir = self._settings.get(
            "default_dir", str(Path.home() / "Downloads" / "VideoConverter")
        )
        dialog = QualitySelectorDialog(video_info, default_dir, self)
        dialog.download_requested.connect(self._on_download_requested)
        dialog.exec()

    def _on_analysis_error(self, error_msg: str):
        """Analiz hatası — status bar'da göster."""
        self._status_bar.showMessage(f"❌ {error_msg}", 5000)

    def _on_download_requested(self, tasks: list[DownloadTask]):
        """Kullanıcı indirmeyi onayladı."""
        for task in tasks:
            self._add_download_card(task)
            task_id = self._queue.add_task(task)

            # Worker bağlantısı — kısa gecikme ile dene (worker başlaması için)
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(200, lambda tid=task_id: self._attach_worker(tid))

    def _add_download_card(self, task: DownloadTask):
        """Kuyruğa kart ekler."""
        card = DownloadCard(task)
        card.cancel_requested.connect(self._on_cancel_requested)
        card.open_folder_requested.connect(self._open_folder)

        # Boş durumu gizle
        if self._empty_state.isVisible():
            self._empty_state.setVisible(False)

        self._queue_layout.addWidget(card)
        self._cards[task.task_id] = card
        self._update_status()

        # Scroll'u en alta taşı
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

    def _attach_worker(self, task_id: str):
        """Queue'daki worker'ı karta bağlar."""
        worker = self._queue.get_worker(task_id)
        card = self._cards.get(task_id)
        if worker and card:
            card.attach_worker(worker)

    def _on_cancel_requested(self, task_id: str):
        """Kart iptal butonuna basıldı."""
        self._queue.cancel_task(task_id)
        self._update_status()

    def _clear_completed(self):
        """Tamamlanan/iptal edilen kartları temizler."""
        from backend.downloader import DownloadStatus
        to_remove = []
        for task_id, card in self._cards.items():
            status = card.get_status()
            if status in (DownloadStatus.FINISHED, DownloadStatus.ERROR, DownloadStatus.CANCELLED):
                to_remove.append(task_id)

        for task_id in to_remove:
            card = self._cards.pop(task_id)
            card.setParent(None)
            card.deleteLater()

        # Boş durumu göster
        if not self._cards:
            self._empty_state.setVisible(True)

        self._update_status()

    # ================================================================
    # Queue Sinyalleri
    # ================================================================

    def _connect_queue_signals(self):
        self._queue.task_started.connect(self._on_task_started)
        self._queue.task_finished.connect(self._on_task_finished)
        self._queue.task_error.connect(self._on_task_error)
        self._queue.queue_empty.connect(self._on_queue_empty)

    def _on_task_started(self, task_id: str):
        self._attach_worker(task_id)
        self._update_status()

    def _on_task_finished(self, task_id: str, output_path: str):
        self._update_status()
        self._status_bar.showMessage(f"✓ İndirme tamamlandı: {os.path.basename(output_path)}", 4000)

        # Veritabanına kaydet
        card = self._cards.get(task_id)
        if card:
            task = card.task
            quality_label = ""
            if task.format_type == "mp4":
                quality_label = f"{task.quality_height}p" if task.quality_height else "best"
            else:
                quality_label = f"{task.mp3_bitrate} kbps"

            try:
                history_db.add_record(
                    url=task.url,
                    title=task.title or os.path.basename(output_path),
                    thumbnail_url=task.thumbnail_url,
                    format_type=task.format_type,
                    quality=quality_label,
                    file_path=output_path
                )
                # Geçmiş sekmesi listesini yenile
                if hasattr(self, "_history_panel"):
                    self._history_panel.refresh_list()
            except Exception as e:
                print(f"[history] Error saving record: {e}")

    def _on_task_error(self, task_id: str, error_msg: str):
        self._update_status()
        self._status_bar.showMessage(f"❌ Hata: {error_msg[:80]}", 5000)

    def _on_queue_empty(self):
        self._status_bar.showMessage("✓ Tüm indirmeler tamamlandı.", 3000)

    # ================================================================
    # Yardımcılar
    # ================================================================

    def _update_status(self):
        active = self._queue.active_count()
        pending = self._queue.pending_count()
        total = len(self._cards)
        parts = []
        if active:
            parts.append(f"{active} aktif")
        if pending:
            parts.append(f"{pending} bekleyen")
        if total:
            parts.append(f"{total} toplam")
            self._count_lbl.setText(f"({', '.join(parts)})")
        else:
            self._count_lbl.setText("")

    def _open_folder(self, path: str):
        """Klasörü dosya gezgininde açar."""
        try:
            if sys.platform == "win32":
                if os.path.isfile(path):
                    subprocess.Popen(["explorer", "/select,", path])
                else:
                    subprocess.Popen(["explorer", path])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass

    def _open_settings(self):
        dialog = SettingsDialog(self._settings, self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()

    def _on_settings_changed(self, new_settings: dict):
        old_theme = self._settings.get("theme")
        self._settings = new_settings

        # Tema değişti mi?
        if new_settings.get("theme") != old_theme:
            self._apply_theme(new_settings["theme"])

        # Paralel indirme sayısı değişti mi?
        self._queue.max_concurrent = new_settings.get("max_concurrent", 3)

    def _on_tab_changed(self, index: int):
        """Sekme değiştiğinde geçmiş listesini tazeler."""
        if index == 1 and hasattr(self, "_history_panel"):
            self._history_panel.refresh_list()

    def _on_history_redownload(self, url: str):
        """Geçmişten tekrar indirmeyi tetikler."""
        self._tabs.setCurrentIndex(0)
        self._url_input.set_url(url)
        self._url_input._on_analyze()

    def closeEvent(self, event):
        """Kapatma — aktif indirme varsa sor."""
        if self._queue.active_count() > 0:
            reply = QMessageBox.question(
                self,
                "Çıkış",
                f"{self._queue.active_count()} aktif indirme var. Çıkmak istiyor musunuz?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return

        self._queue.cancel_all()
        event.accept()
