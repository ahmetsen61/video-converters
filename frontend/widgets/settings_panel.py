"""
settings_panel.py
-----------------
Ayarlar dialog'u. Tema, paralel indirme sayısı,
varsayılan klasör ve MP3 kalitesi ayarlarını yönetir.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QSpinBox, QComboBox,
    QFrame, QFileDialog, QLineEdit, QCheckBox,
)


DEFAULT_SETTINGS = {
    "theme": "dark",
    "max_concurrent": 3,
    "default_dir": str(Path.home() / "Downloads" / "VideoConverter"),
    "mp3_bitrate": "320",
}

SETTINGS_PATH = os.path.join(
    os.path.expanduser("~"), ".videoconverter", "settings.json"
)


def load_settings() -> dict:
    """Ayarları dosyadan yükler. Yoksa varsayılanları döndürür."""
    try:
        if os.path.isfile(SETTINGS_PATH):
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # Eksik anahtarları varsayılanla doldur
            return {**DEFAULT_SETTINGS, **saved}
    except Exception:
        pass
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict):
    """Ayarları dosyaya kaydeder."""
    try:
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


class SettingsDialog(QDialog):
    """Ayarlar dialog penceresi."""

    settings_changed = pyqtSignal(dict)

    def __init__(self, current_settings: dict, parent=None):
        super().__init__(parent)
        self._settings = current_settings.copy()
        self.setWindowTitle("Ayarlar")
        self.setMinimumWidth(460)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Başlık
        title = QLabel("⚙  Ayarlar")
        title.setProperty("class", "title")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        sep = QFrame(); sep.setProperty("class", "separator"); sep.setFixedHeight(1)
        layout.addWidget(sep)

        # Grid ayarlar
        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        grid.setVerticalSpacing(16)
        grid.setHorizontalSpacing(16)

        row = 0

        # ---- Tema ----
        grid.addWidget(self._make_label("Tema:"), row, 0)
        self._theme_combo = QComboBox()
        self._theme_combo.addItem("🌙  Koyu", userData="dark")
        self._theme_combo.addItem("☀️  Açık", userData="light")
        idx = 0 if self._settings.get("theme") == "dark" else 1
        self._theme_combo.setCurrentIndex(idx)
        grid.addWidget(self._theme_combo, row, 1)
        row += 1

        # ---- Paralel indirme ----
        grid.addWidget(self._make_label("Paralel İndirme:"), row, 0)
        self._concurrent_spin = QSpinBox()
        self._concurrent_spin.setRange(1, 10)
        self._concurrent_spin.setValue(self._settings.get("max_concurrent", 3))
        self._concurrent_spin.setSuffix(" adet")
        grid.addWidget(self._concurrent_spin, row, 1)
        row += 1

        # ---- Varsayılan klasör ----
        grid.addWidget(self._make_label("Varsayılan Klasör:"), row, 0)
        folder_row = QHBoxLayout()
        self._folder_input = QLineEdit(self._settings.get("default_dir", ""))
        self._folder_input.setReadOnly(True)
        browse_btn = QPushButton("Gözat")
        browse_btn.setProperty("class", "secondary")
        browse_btn.setFixedWidth(70)
        browse_btn.clicked.connect(self._browse_folder)
        folder_row.addWidget(self._folder_input)
        folder_row.addWidget(browse_btn)
        folder_widget = QFrame()
        folder_widget.setLayout(folder_row)
        grid.addWidget(folder_widget, row, 1)
        row += 1

        # ---- MP3 Kalitesi ----
        grid.addWidget(self._make_label("MP3 Kalitesi:"), row, 0)
        self._mp3_combo = QComboBox()
        for bitrate in ["320 kbps", "256 kbps", "192 kbps", "128 kbps"]:
            self._mp3_combo.addItem(bitrate, userData=bitrate.split()[0])
        current_br = self._settings.get("mp3_bitrate", "320")
        for i in range(self._mp3_combo.count()):
            if self._mp3_combo.itemData(i) == current_br:
                self._mp3_combo.setCurrentIndex(i)
                break
        grid.addWidget(self._mp3_combo, row, 1)
        row += 1

        layout.addLayout(grid)

        sep2 = QFrame(); sep2.setProperty("class", "separator"); sep2.setFixedHeight(1)
        layout.addWidget(sep2)

        # Butonlar
        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("İptal")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Kaydet")
        save_btn.setMinimumWidth(100)
        save_btn.clicked.connect(self._on_save)

        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _make_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lbl.setProperty("class", "subtitle")
        return lbl

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Varsayılan Klasör Seç",
            self._settings.get("default_dir", str(Path.home()))
        )
        if folder:
            self._folder_input.setText(folder)

    def _on_save(self):
        self._settings["theme"] = self._theme_combo.currentData()
        self._settings["max_concurrent"] = self._concurrent_spin.value()
        self._settings["default_dir"] = self._folder_input.text()
        self._settings["mp3_bitrate"] = self._mp3_combo.currentData()

        save_settings(self._settings)
        self.settings_changed.emit(self._settings.copy())
        self.accept()
