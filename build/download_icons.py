import os
import urllib.request

ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icons")
os.makedirs(ICON_DIR, exist_ok=True)

ICONS = {
    # Dark Theme Icons (White)
    "settings_white.png": "https://img.icons8.com/ios-glyphs/30/ffffff/settings.png",
    "paste_white.png": "https://img.icons8.com/ios-glyphs/30/ffffff/paste.png",
    "trash_white.png": "https://img.icons8.com/ios-glyphs/30/ffffff/trash.png",
    "folder_white.png": "https://img.icons8.com/ios-glyphs/30/ffffff/folder-open.png",
    "sun_white.png": "https://img.icons8.com/ios-glyphs/30/ffffff/sun.png",
    "moon_white.png": "https://img.icons8.com/ios-glyphs/30/ffffff/moon.png",
    "download_white.png": "https://img.icons8.com/ios-glyphs/120/ffffff/download.png",
    "search_white.png": "https://img.icons8.com/ios-glyphs/30/ffffff/search.png",
    "download_tab_white.png": "https://img.icons8.com/ios-glyphs/30/ffffff/download.png",
    "history_tab_white.png": "https://img.icons8.com/ios-glyphs/30/ffffff/historical.png",
    
    # Light Theme Icons (Dark gray/black)
    "settings_dark.png": "https://img.icons8.com/ios-glyphs/30/111827/settings.png",
    "paste_dark.png": "https://img.icons8.com/ios-glyphs/30/111827/paste.png",
    "trash_dark.png": "https://img.icons8.com/ios-glyphs/30/111827/trash.png",
    "folder_dark.png": "https://img.icons8.com/ios-glyphs/30/111827/folder-open.png",
    "sun_dark.png": "https://img.icons8.com/ios-glyphs/30/111827/sun.png",
    "moon_dark.png": "https://img.icons8.com/ios-glyphs/30/111827/moon.png",
    "download_dark.png": "https://img.icons8.com/ios-glyphs/120/111827/download.png",
    "search_dark.png": "https://img.icons8.com/ios-glyphs/30/111827/search.png",
    "download_tab_dark.png": "https://img.icons8.com/ios-glyphs/30/111827/download.png",
    "history_tab_dark.png": "https://img.icons8.com/ios-glyphs/30/111827/historical.png",
}

print("İkonlar indiriliyor...")
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for filename, url in ICONS.items():
    filepath = os.path.join(ICON_DIR, filename)
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response, open(filepath, 'wb') as out_file:
            out_file.write(response.read())
        print(f"Başarılı: {filename}")
    except Exception as e:
        print(f"Hata: {filename} indirilemedi! {e}")

print("İkon indirme işlemi tamamlandı.")
