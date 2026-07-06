@echo off
REM build.bat - VideoConverter Build Scripti
REM Kullanim: build\build.bat
REM Cikti:    dist\VideoConverter.exe

setlocal EnableDelayedExpansion
for %%i in ("%~dp0..") do set "ROOT=%%~fi"
set "START_TIME=%TIME%"

echo.
echo ================================================
echo   VideoConverter - Build Scripti
echo ================================================
echo.

REM ================================================================
REM 1. Python Kontrolu
REM ================================================================
set "PYTHON_EXE="

REM Once sanal ortam kontrol et
if exist "%ROOT%\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%ROOT%\venv\Scripts\python.exe"
    echo [OK] Python bulundu - venv
    goto :python_ok
)
where python >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=python"
    echo [OK] Python bulundu - sistem
    goto :python_ok
)
echo [HATA] Python bulunamadi. Python 3.10+ yukleyin.
exit /b 1
:python_ok

REM pip yolu
set "PIP_EXE="
if exist "%ROOT%\venv\Scripts\pip.exe" (
    set "PIP_EXE=%ROOT%\venv\Scripts\pip.exe"
) else (
    set "PIP_EXE=pip"
)

REM ================================================================
REM 2. PyInstaller Kontrolu
REM ================================================================
"%PYTHON_EXE%" -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] PyInstaller bulunamadi, yukleniyor...
    "%PIP_EXE%" install pyinstaller --quiet
    if %errorlevel% neq 0 (
        echo [HATA] PyInstaller yuklenemedi.
        exit /b 1
    )
)
echo [OK] PyInstaller hazir

REM ================================================================
REM 3. Bagimlilik Kontrolu
REM ================================================================
"%PYTHON_EXE%" -c "import yt_dlp" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] yt-dlp bulunamadi, yukleniyor...
    "%PIP_EXE%" install -r "%ROOT%\requirements.txt" --quiet
)
"%PYTHON_EXE%" -c "import PyQt6" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] PyQt6 bulunamadi, yukleniyor...
    "%PIP_EXE%" install PyQt6 --quiet
)
echo [OK] Bagimlilıklar hazir

REM ================================================================
REM 4. FFmpeg Kontrolu
REM ================================================================
set "FFMPEG_DIR=%ROOT%\assets\ffmpeg"
set "FFMPEG_EXE=%FFMPEG_DIR%\ffmpeg.exe"
set "FFPROBE_EXE=%FFMPEG_DIR%\ffprobe.exe"

if not exist "%FFMPEG_EXE%" (
    echo.
    echo [!] FFmpeg bulunamadi: assets\ffmpeg\ffmpeg.exe
    echo.
    echo     Secenekler:
    echo     1. Otomatik indir (gyan.dev, yaklasik 90 MB, onerilen)
    echo     2. Zaten koydum, devam et
    echo     3. FFmpeg olmadan build al (MP3 ve 1080p+ calismayabilir)
    echo.
    set /p "CHOICE=Seciminiz (1/2/3): "

    if "%CHOICE%"=="1" goto :ffmpeg_download
    if "%CHOICE%"=="2" goto :ffmpeg_manual
    if "%CHOICE%"=="3" goto :ffmpeg_skip
    echo [HATA] Gecersiz secim.
    exit /b 1

    :ffmpeg_download
    echo.
    echo [*] FFmpeg indiriliyor...
    if not exist "%FFMPEG_DIR%" mkdir "%FFMPEG_DIR%"
    set "ZIP_URL=https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    set "ZIP_PATH=%TEMP%\ffmpeg-release.zip"
    set "UNZIP_DIR=%TEMP%\ffmpeg-unzip"
    echo     Indiriliyor, lutfen bekleyin (bu birkaç dakika surebilir)...
    powershell -NoProfile -Command "Invoke-WebRequest -Uri '%ZIP_URL%' -OutFile '%ZIP_PATH%' -UseBasicParsing"
    if %errorlevel% neq 0 (
        echo [HATA] FFmpeg indirilemedi.
        echo        Manuel olarak https://www.gyan.dev/ffmpeg/builds/ adresinden
        echo        ffmpeg-release-essentials.zip indirip assets\ffmpeg\ icine cikarin.
        exit /b 1
    )
    if exist "%UNZIP_DIR%" rmdir /s /q "%UNZIP_DIR%"
    powershell -NoProfile -Command "Expand-Archive -Path '%ZIP_PATH%' -DestinationPath '%UNZIP_DIR%' -Force"
    for /r "%UNZIP_DIR%" %%f in (ffmpeg.exe)  do copy "%%f" "%FFMPEG_EXE%" /y >nul
    for /r "%UNZIP_DIR%" %%f in (ffprobe.exe) do copy "%%f" "%FFPROBE_EXE%" /y >nul
    if exist "%FFMPEG_EXE%" (
        echo [OK] ffmpeg.exe kopyalandi
    ) else (
        echo [HATA] ffmpeg.exe kopyalanamadi.
        exit /b 1
    )
    if exist "%FFPROBE_EXE%" echo [OK] ffprobe.exe kopyalandi
    del "%ZIP_PATH%" >nul 2>&1
    rmdir /s /q "%UNZIP_DIR%" >nul 2>&1
    goto :ffmpeg_ok

    :ffmpeg_manual
    if not exist "%FFMPEG_EXE%" (
        echo [HATA] Hala bulunamadi: %FFMPEG_EXE%
        exit /b 1
    )
    echo [OK] FFmpeg bulundu.
    goto :ffmpeg_ok

    :ffmpeg_skip
    echo [!] FFmpeg olmadan devam ediliyor.
    goto :ffmpeg_ok

    :ffmpeg_ok
) else (
    echo [OK] FFmpeg: %FFMPEG_EXE%
    if exist "%FFPROBE_EXE%" echo [OK] FFprobe: %FFPROBE_EXE%
)

REM ================================================================
REM 5. Eski Build Temizle
REM ================================================================
echo.
echo [*] Eski build dosyalari temizleniyor...
set "DIST_DIR=%ROOT%\dist"
set "BUILD_CACHE=%ROOT%\build\_pyinstaller"
if exist "%DIST_DIR%"    rmdir /s /q "%DIST_DIR%"
if exist "%BUILD_CACHE%" rmdir /s /q "%BUILD_CACHE%"

REM ================================================================
REM 6. PyInstaller Calistir
REM ================================================================
echo.
echo [*] PyInstaller calistiriliyor...
echo     Bu islem 3-8 dakika surebilir...
echo.

set "SPEC_FILE=%ROOT%\build\build.spec"
cd /d "%ROOT%"
"%PYTHON_EXE%" -m PyInstaller "%SPEC_FILE%" --clean --noconfirm --workpath "build\_pyinstaller"

if %errorlevel% neq 0 (
    echo.
    echo [HATA] Build basarisiz. Yukaridaki hatalari inceleyin.
    exit /b 1
)

REM ================================================================
REM 7. Sonuc
REM ================================================================
set "EXE_PATH=%ROOT%\dist\VideoConverter.exe"

if exist "%EXE_PATH%" (
    for %%f in ("%EXE_PATH%") do set "FILE_SIZE=%%~zf"
    set /a "FILE_SIZE_MB=%FILE_SIZE% / 1048576"

    echo.
    echo ================================================
    echo   BUILD BASARILI!
    echo ================================================
    echo.
    echo   Dosya : dist\VideoConverter.exe
    echo   Boyut : %FILE_SIZE_MB% MB
    echo.
    echo   GitHub Releases sayfasina yukleyebilirsiniz.
    echo.

    set /p "OPEN=dist/ klasoru acilsin mi? (e/h): "
    if /i "%OPEN%"=="e" start explorer.exe "%ROOT%\dist"
) else (
    echo [HATA] VideoConverter.exe olusturulamadi.
    exit /b 1
)

endlocal
