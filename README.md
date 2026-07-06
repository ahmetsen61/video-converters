# 🎬 VideoConverter

YouTube, Instagram ve TikTok videolarını MP4 ve MP3 formatında indirebilen, modern arayüzlü masaüstü uygulaması.

![Platform](https://img.shields.io/badge/Platform-Windows-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ✨ Özellikler

- 🎥 **YouTube, Instagram, TikTok** desteği (Playlist dahil)
- 📹 **MP4** (video) ve 🎵 **MP3** (ses) format seçimi
- 🎯 **Kalite seçeneği**: 4K, 1440p, 1080p, 720p, 480p, 360p
- 📊 **Gerçek zamanlı indirme ilerleme çubuğu** (hız + ETA)
- 🔄 **Çoklu indirme kuyruğu** (paralel indirme desteği)
- 📁 **Özel klasör seçimi**
- 🌙 **Koyu / Açık tema** desteği
- ❌ **Hata yönetimi** (geçersiz link, private video, bağlantı hatası)
- 📦 **Kurulum gerektirmez** — Tek `.exe` dosyası

---

## 🚀 Hızlı Başlangıç (Kullanıcı için)

1. [Releases](https://github.com/kullaniciadi/videoconverter/releases) sayfasından `VideoConverter.exe` dosyasını indirin
2. Çift tıklayın — kurulum gerekmez!
3. Video linkini yapıştırın ve indirin

> **Not**: FFmpeg uygulama içine gömülüdür, ayrıca kurulum gerekmez.

---

## 🛠️ Geliştirici Kurulumu

### Gereksinimler

| Araç | Versiyon | İndirme |
|------|----------|---------|
| Python | 3.10+ | [python.org](https://www.python.org/downloads/) |
| FFmpeg | Son sürüm | [ffmpeg.org](https://ffmpeg.org/download.html) |

### Kurulum Adımları

```bash
# 1. Repoyu klonla
git clone https://github.com/kullaniciadi/videoconverter.git
cd videoconverter

# 2. Virtual environment oluştur
python -m venv venv

# Windows:
venv\Scripts\activate

# 3. Bağımlılıkları yükle
pip install -r requirements.txt

# 4. FFmpeg'i yerleştir (geliştirme ortamı için)
# FFmpeg'i indirip assets/ffmpeg/ klasörüne koy:
#   assets/ffmpeg/ffmpeg.exe
#   assets/ffmpeg/ffprobe.exe
# VEYA sistem PATH'inde FFmpeg varsa otomatik bulunur.

# 5. Uygulamayı başlat
python main.py
```

---

## 📦 Build (Tek .exe Oluşturma)

### Ön Koşullar

1. `requirements.txt` kurulu olmalı (`pip install -r requirements.txt`)
2. `assets/ffmpeg/ffmpeg.exe` ve `assets/ffmpeg/ffprobe.exe` mevcut olmalı
3. PowerShell 5.0+ (Windows'ta varsayılan)

### Build Komutu

```cmd
REM Komut istemi (cmd.exe) veya PowerShell'de calistirin:
build\build.bat
```

Script FFmpeg'i bulamazsa 3 secenek sunar:
1. **Otomatik indir** — gyan.dev'den ~90 MB FFmpeg indirir (onerilen)
2. **Elle koydum** — `assets\ffmpeg\` klasorune onceden koyduysan
3. **FFmpeg olmadan** — MP3 ve 1080p+ calismaz, ama exe olusur

### Manuel Build

```cmd
venv\Scripts\python -m PyInstaller build\build.spec --clean --noconfirm
```

### Çıktı

```
dist/
└── VideoConverter.exe   (~80-100 MB, kurulum gerektirmez)
```

> Build yaklaşık 2-5 dakika sürer. `dist/VideoConverter.exe` dosyasını GitHub Releases'e yükleyebilirsiniz.

---

## 📁 Proje Yapısı

```
videoconverter/
├── backend/
│   ├── analyzer.py          # URL analiz motoru (yt-dlp)
│   ├── downloader.py        # İndirme işçisi (QThread)
│   ├── queue_manager.py     # Çoklu indirme kuyruğu
│   └── ffmpeg_utils.py      # FFmpeg yolu yönetimi
├── frontend/
│   ├── main_window.py       # Ana pencere
│   ├── widgets/
│   │   ├── url_input.py     # URL giriş alanı
│   │   ├── quality_selector.py  # Kalite/format seçimi
│   │   ├── download_card.py # İndirme kart bileşeni
│   │   └── settings_panel.py    # Ayarlar paneli
│   └── styles/
│       ├── dark_theme.qss   # Koyu tema
│       └── light_theme.qss  # Açık tema
├── assets/
│   ├── ffmpeg/              # FFmpeg binary (build için)
│   └── app_icon.ico
├── build/
│   ├── build.spec           # PyInstaller spec
│   └── build.ps1            # Build scripti
├── main.py                  # Giriş noktası
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🔧 Kullanım

1. **Link Yapıştır**: YouTube/Instagram/TikTok URL'sini giriş alanına yapıştırın
2. **Analiz Et**: "Analiz Et" butonuna tıklayın — mevcut kaliteler listelenir
3. **Format Seç**: MP4 (video) veya MP3 (ses) seçin
4. **Kalite Seç**: İstediğiniz çözünürlüğü seçin (4K, 1080p, vb.)
5. **Klasör Seç**: İndirme konumunu belirleyin (varsayılan: `~/İndirilenler/VideoConverter`)
6. **İndir**: "İndir" butonuna tıklayın — ilerleme gerçek zamanlı izlenir

### Playlist Desteği

Playlist URL'si girildiğinde seçim ekranı açılır: tüm playlist veya belirli videolar seçilebilir.

---

## ⚙️ Ayarlar

| Ayar | Varsayılan |
|------|-----------|
| Paralel indirme sayısı | 3 |
| Varsayılan klasör | `~/İndirilenler/VideoConverter` |
| Tema | Koyu |
| MP3 kalitesi | 320 kbps |

---

## 🐛 Bilinen Sınırlamalar

- **Private/Kısıtlı içerik**: Giriş gerektiren videolar indirilemez
- **DRM korumalı içerik**: Netflix, Disney+ gibi platformlar desteklenmez
- **Instagram**: Bazı Reels/Story'ler API kısıtlamaları nedeniyle indirilemeyebilir

---

## 📜 Lisans

MIT License — Detaylar için [LICENSE](LICENSE) dosyasına bakın.

---

## 🙏 Teşekkürler

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — İndirme motoru
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) — UI framework
- [FFmpeg](https://ffmpeg.org/) — Medya dönüştürme
