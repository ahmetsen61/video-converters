"""
main.py
-------
VideoConverter uygulama giriş noktası.

Kullanım:
    python main.py

PyInstaller ile paketlendiğinde bu dosya entry point olarak kullanılır.
"""

import sys
import os

# PyInstaller paketi içinde yol düzeltmesi
if getattr(sys, 'frozen', False):
    # Uygulama paketi içindeyiz
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Kök dizini sys.path'e ekle (paket importları için)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from frontend.main_window import MainWindow


def main():
    # Windows'ta taskbar ikonu sorunu düzeltmesi
    if sys.platform == "win32":
        try:
            import ctypes
            myappid = "videoconverter.desktop.app.v1.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    # PyQt6'da HiDPI varsayılan olarak etkin — özel attribute gerekmez
    app = QApplication(sys.argv)
    app.setApplicationName("VideoConverter")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("VideoConverter")

    # Uygulama ikonu
    icon_path = os.path.join(BASE_DIR, "assets", "app_icon.ico")
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Ana pencereyi oluştur ve göster
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
