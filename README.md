# 🎬 VideoConverter

YouTube, Instagram ve TikTok videolarını MP4 ve MP3 formatında indirebilen, modern arayüzlü, SQLite tabanlı geçmiş desteğine sahip güçlü bir masaüstü uygulaması.

![Platform](https://img.shields.io/badge/Platform-Windows-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ✨ Özellikler

- 🎥 **YouTube, Instagram, TikTok** desteği (Playlist dahil)
- 📹 **MP4** (video) ve 🎵 **MP3** (ses) format seçimi
- 🎯 **Kalite seçeneği**: 4K, 1440p, 1080p, 720p, 480p, 360p (Çözünürlüğe göre tekil listeleme ve tam eşleşme)
- 📊 **Gerçek zamanlı indirme ilerleme çubuğu** (hız + ETA)
- 🔄 **Çoklu indirme kuyruğu** (paralel indirme desteği)
- 📁 **Özel klasör seçimi**
- 🌙 **Koyu / Açık tema** desteği (Header üzerinden anında değişim)
- 📜 **İndirme Geçmişi (SQLite)**:
  - İndirilen tüm videoları görseli, başlığı, tarihi ve kalitesiyle listeleyin.
  - "Klasörü Aç", "Tekrar İndir" ve "Geçmişten Sil" aksiyonları.
  - Arama filtresi (başlığa veya linke göre).
  - Mükerrer indirme koruması (Diskte dosya duruyorsa "Dosyayı Aç" / "Yine de İndir" uyarısı).
- ❌ **Hata yönetimi** (geçersiz link, private video, bağlantı hatası)
- 📦 **Kurulum gerektirmez** — Tek `.exe` dosyası (FFmpeg gömülü)

---

## 🚀 Hızlı Başlangıç (Kullanıcı için)

1. [Releases](https://github.com/ahmetsen61/video-converters/releases) sayfasından `VideoConverter.exe` dosyasını indirin.
2. Çift tıklayın — kurulum gerekmez!
3. Video linkini yapıştırın ve indirin.

> **Not**: FFmpeg ve SQLite kütüphaneleri uygulama içine gömülüdür, ayrıca kurulum gerekmez. Windows taskbar ikonu otomatik olarak mor klaket şeklinde ayarlanır.

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
git clone https://github.com/ahmetsen61/video-converters.git
cd video-converters

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
2. PowerShell veya CMD komut satırı
3. (Opsiyonel) `assets/ffmpeg/ffmpeg.exe` mevcut olmalı (bulunamazsa otomatik indirilir)

### Build Komutu

```cmd
REM Komut istemi (cmd.exe) veya PowerShell'de çalıştırın:
build\build.bat
```

Script FFmpeg'i bulamazsa size 3 seçenek sunar:
1. **Otomatik indir** — gyan.dev'den ~90 MB FFmpeg zip dosyasını çeker, açar ve kopyalar (önerilen)
2. **Elle koydum** — `assets\ffmpeg\` klasörüne önceden kopyaladıysanız devam eder
3. **FFmpeg olmadan** — MP3 dönüştürme ve 1080p+ indirme birleştirme çalışmaz, ama exe derlenir

### Manuel Derleme

```cmd
venv\Scripts\python -m PyInstaller build\build.spec --clean --noconfirm
```

### Çıktı

```
dist/
└── VideoConverter.exe   (~115 MB, kurulum gerektirmez, FFmpeg gömülü)
```

---

## 📁 Proje Yapısı

```
video-converters/
├── backend/
│   ├── analyzer.py          # URL analiz motoru (yt-dlp)
│   ├── downloader.py        # İndirme işçisi (QThread)
│   ├── queue_manager.py     # Çoklu paralel indirme kuyruğu
│   ├── history_db.py        # SQLite geçmiş veritabanı CRUD işlemleri
│   └── ffmpeg_utils.py      # FFmpeg yolu ve konum yönetimi
├── frontend/
│   ├── main_window.py       # Ana pencere ve QTabWidget sekmeleri
│   ├── widgets/
│   │   ├── url_input.py     # URL giriş alanı
│   │   ├── quality_selector.py  # Kalite/format seçimi dialoğu
│   │   ├── download_card.py # Aktif indirme kuyruğu kart bileşeni
│   │   ├── history_panel.py # Geçmiş sekmesi, arama ve HistoryCard bileşenleri
│   │   └── settings_panel.py    # Ayarlar dialoğu
│   └── styles/
│       ├── dark_theme.qss   # Koyu tema tasarımı
│       └── light_theme.qss  # Açık tema tasarımı
├── assets/
│   ├── ffmpeg/              # FFmpeg binary (build sırasında içine gömülür)
│   ├── app_icon.ico         # Çok çözünürlüklü Windows uygulama ikonu
│   └── app_icon.jpg         # Kaynak görsel
├── build/
│   ├── build.spec           # PyInstaller spec dosyası
│   ├── build.bat            # Otomatik derleyici script
│   └── convert_icon.py      # JPG ikonunu ICO formatına çeviren araç
├── main.py                  # Uygulama giriş noktası (Taskbar fix içerir)
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🔧 Kullanım

1. **Link Yapıştır**: YouTube/Reels/TikTok URL'sini yapıştırıp "Analiz Et" deyin.
2. **Geçmiş Kontrolü**: Link önceden indirilmiş ve diskte duruyorsa size "Dosyayı Aç" / "Yine de İndir" penceresi gelir.
3. **Format & Kalite Seç**: MP4 seçerseniz dilediğiniz video kalitesini; MP3 seçerseniz dilediğiniz ses bitrate seçeneğini (320kbps, vb.) belirleyin.
4. **İndir**: İndirmeler eşzamanlı olarak kuyruğa alınır ve UI kilitlenmeden tamamlanır.
5. **Geçmişi Yönet**: "Geçmiş" sekmesinden indirdiğiniz videonun konumuna hızlıca gidin, yeniden indirmeyi başlatın ya da geçmişten silin.

---

## ⚙️ Ayarlar

| Ayar | Varsayılan | Açıklama |
|------|-----------|----------|
| Paralel indirme sayısı | 3 | Aynı anda indirilecek maksimum video sayısı |
| Varsayılan klasör | `~/Downloads/VideoConverter` | Dosyaların kaydedileceği dizin |
| Tema | Koyu | Açık veya Koyu tema seçimi |
| MP3 kalitesi | 320 kbps | MP3 indirmeleri için ses sıkıştırma kalitesi |

---

## 📜 Lisans

MIT License — Detaylar için [LICENSE](LICENSE) dosyasına bakın.

---

## 🙏 Teşekkürler

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — İndirme motoru
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) — UI framework
- [FFmpeg](https://ffmpeg.org/) — Medya dönüştürme ve birleştirme
