# build.ps1 — VideoConverter Build Scripti
# Kullanim: .\build\build.ps1
# Cikti:    dist\VideoConverter.exe
#
# Gereksinimler:
#   - Python 3.10+
#   - pip install -r requirements.txt yapilmis olmali
#   - (Opsiyonel) assets/ffmpeg/ffmpeg.exe — otomatik indirilir

$ErrorActionPreference = "Stop"
$StartTime = Get-Date

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  VideoConverter - Build Scripti" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Proje kok dizini (bu scriptin bir ustu)
$ROOT = Split-Path -Parent $PSScriptRoot

# ================================================================
# 1. Python Kontrolu
# ================================================================
$pythonExe = $null

# Once sanal ortam kontrol et
$venvPython = Join-Path $ROOT "venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonExe = $venvPython
    $pyVer = & $pythonExe --version 2>&1
    Write-Host "[OK] $pyVer (venv)" -ForegroundColor Green
} else {
    # Sistem Python
    $sysCheck = Get-Command python -ErrorAction SilentlyContinue
    if ($sysCheck) {
        $pythonExe = "python"
        $pyVer = & python --version 2>&1
        Write-Host "[OK] $pyVer (sistem)" -ForegroundColor Green
    } else {
        Write-Host "[HATA] Python bulunamadi! Python 3.10+ yukleyin." -ForegroundColor Red
        exit 1
    }
}

# pip yolu
$pipExe = $null
$venvPip = Join-Path $ROOT "venv\Scripts\pip.exe"
if (Test-Path $venvPip) {
    $pipExe = $venvPip
} else {
    $pipExe = "pip"
}

# ================================================================
# 2. PyInstaller Kontrolu
# ================================================================
$piCheck = & $pythonExe -c "import PyInstaller; print(PyInstaller.__version__)" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] PyInstaller bulunamadi, yukleniyor..." -ForegroundColor Yellow
    & $pipExe install pyinstaller --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[HATA] PyInstaller yuklenemedi." -ForegroundColor Red
        exit 1
    }
}
$piCheck = & $pythonExe -c "import PyInstaller; print(PyInstaller.__version__)" 2>&1
Write-Host "[OK] PyInstaller $piCheck" -ForegroundColor Green

# ================================================================
# 3. yt-dlp / PyQt6 Kontrolu
# ================================================================
$ytdlpCheck = & $pythonExe -c "import yt_dlp" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] yt-dlp bulunamadi, yukleniyor..." -ForegroundColor Yellow
    & $pipExe install -r (Join-Path $ROOT "requirements.txt") --quiet
}

$pyqtCheck = & $pythonExe -c "import PyQt6" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] PyQt6 bulunamadi, yukleniyor..." -ForegroundColor Yellow
    & $pipExe install PyQt6 --quiet
}
Write-Host "[OK] Bagimlilıklar hazir" -ForegroundColor Green

# ================================================================
# 4. FFmpeg Kontrolu ve Otomatik Indirme
# ================================================================
$ffmpegDir  = Join-Path $ROOT "assets\ffmpeg"
$ffmpegExe  = Join-Path $ffmpegDir "ffmpeg.exe"
$ffprobeExe = Join-Path $ffmpegDir "ffprobe.exe"

if (-not (Test-Path $ffmpegExe)) {
    Write-Host ""
    Write-Host "[!] FFmpeg bulunamadi: assets\ffmpeg\ffmpeg.exe" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "    Secenekler:" -ForegroundColor White
    Write-Host "    [1] Otomatik indir (gyan.dev — ~90 MB, onerilen)" -ForegroundColor White
    Write-Host "    [2] Elle koydum, devam et" -ForegroundColor White
    Write-Host "    [3] FFmpeg olmadan build al (MP3 ve 1080p+ calismiyor)" -ForegroundColor White
    Write-Host ""
    $choice = Read-Host "Seciminiz (1/2/3)"

    switch ($choice) {
        "1" {
            Write-Host ""
            Write-Host "[*] FFmpeg indiriliyor..." -ForegroundColor Cyan
            
            New-Item -ItemType Directory -Force -Path $ffmpegDir | Out-Null
            
            $zipUrl  = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
            $zipPath = Join-Path $env:TEMP "ffmpeg-release.zip"
            $unzipDir = Join-Path $env:TEMP "ffmpeg-unzip"
            
            Write-Host "    Indiriliyor: $zipUrl" -ForegroundColor Gray
            try {
                Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing
            } catch {
                Write-Host "[HATA] Indirme basarisiz: $_" -ForegroundColor Red
                Write-Host "       Manuel olarak https://www.gyan.dev/ffmpeg/builds/ adresinden" -ForegroundColor Yellow
                Write-Host "       ffmpeg-release-essentials.zip indirip assets\ffmpeg\ icine cikarin." -ForegroundColor Yellow
                exit 1
            }
            
            Write-Host "    Aciliyor..." -ForegroundColor Gray
            if (Test-Path $unzipDir) { Remove-Item -Recurse -Force $unzipDir }
            Expand-Archive -Path $zipPath -DestinationPath $unzipDir -Force
            
            # ffmpeg.exe ve ffprobe.exe bul
            $ffmpegFound  = Get-ChildItem -Path $unzipDir -Recurse -Filter "ffmpeg.exe"  | Select-Object -First 1
            $ffprobeFound = Get-ChildItem -Path $unzipDir -Recurse -Filter "ffprobe.exe" | Select-Object -First 1
            
            if ($ffmpegFound) {
                Copy-Item $ffmpegFound.FullName  -Destination $ffmpegExe  -Force
                Write-Host "[OK] ffmpeg.exe kopyalandi" -ForegroundColor Green
            } else {
                Write-Host "[HATA] ffmpeg.exe zip icinde bulunamadi." -ForegroundColor Red
                exit 1
            }
            
            if ($ffprobeFound) {
                Copy-Item $ffprobeFound.FullName -Destination $ffprobeExe -Force
                Write-Host "[OK] ffprobe.exe kopyalandi" -ForegroundColor Green
            }
            
            # Temizlik
            Remove-Item $zipPath -ErrorAction SilentlyContinue
            Remove-Item -Recurse -Force $unzipDir -ErrorAction SilentlyContinue
        }
        "2" {
            if (-not (Test-Path $ffmpegExe)) {
                Write-Host "[HATA] Hala bulunamadi: $ffmpegExe" -ForegroundColor Red
                exit 1
            }
            Write-Host "[OK] FFmpeg bulundu." -ForegroundColor Green
        }
        "3" {
            Write-Host "[!] FFmpeg olmadan devam ediliyor." -ForegroundColor Yellow
        }
        default {
            Write-Host "[HATA] Gecersiz secim." -ForegroundColor Red
            exit 1
        }
    }
} else {
    Write-Host "[OK] FFmpeg: $ffmpegExe" -ForegroundColor Green
    if (Test-Path $ffprobeExe) {
        Write-Host "[OK] FFprobe: $ffprobeExe" -ForegroundColor Green
    }
}

# ================================================================
# 5. Eski Build Dosyalarini Temizle
# ================================================================
Write-Host ""
Write-Host "[*] Eski build dosyalari temizleniyor..." -ForegroundColor Gray

$distDir    = Join-Path $ROOT "dist"
$buildCache = Join-Path $ROOT "build\_pyinstaller"

if (Test-Path $distDir)    { Remove-Item -Recurse -Force $distDir }
if (Test-Path $buildCache) { Remove-Item -Recurse -Force $buildCache }

# ================================================================
# 6. PyInstaller Calistir
# ================================================================
Write-Host ""
Write-Host "[*] PyInstaller calistiriliyor..." -ForegroundColor Cyan
Write-Host "    (Bu islem 3-8 dakika surebilir...)" -ForegroundColor Gray
Write-Host ""

$specFile = Join-Path $ROOT "build\build.spec"

Set-Location $ROOT

& $pythonExe -m PyInstaller $specFile --clean --noconfirm --workpath "build\_pyinstaller"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[HATA] Build basarisiz! PyInstaller hata verdi." -ForegroundColor Red
    Write-Host "       Yukaridaki hata mesajlarini inceleyin." -ForegroundColor Yellow
    exit 1
}

# ================================================================
# 7. Sonuc
# ================================================================
$exePath = Join-Path $ROOT "dist\VideoConverter.exe"

if (Test-Path $exePath) {
    $fileSize = [math]::Round((Get-Item $exePath).Length / 1MB, 1)
    $elapsed  = [math]::Round(((Get-Date) - $StartTime).TotalSeconds, 1)

    Write-Host ""
    Write-Host "================================================" -ForegroundColor Green
    Write-Host "  BUILD BASARILI!" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Dosya : dist\VideoConverter.exe" -ForegroundColor White
    Write-Host "  Boyut : $fileSize MB" -ForegroundColor White
    Write-Host "  Sure  : $elapsed saniye" -ForegroundColor White
    Write-Host ""
    Write-Host "  GitHub Releases'e yukleyebilirsiniz." -ForegroundColor Cyan
    Write-Host ""

    $openFolder = Read-Host "dist/ klasoru acilsin mi? (e/h)"
    if ($openFolder -eq "e" -or $openFolder -eq "E") {
        Start-Process explorer.exe -ArgumentList (Join-Path $ROOT "dist")
    }
} else {
    Write-Host "[HATA] VideoConverter.exe olusturulamadi." -ForegroundColor Red
    exit 1
}
