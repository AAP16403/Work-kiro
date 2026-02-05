# Privacy Screen Guard - Build & Deployment Guide

## Overview
Privacy Screen Guard is a privacy-focused screen protection tool that detects sensitive content via OCR and blurs the screen.

## Requirements
- **Python 3.8+**
- **Tesseract-OCR** (required for text detection)
- **PIL/Pillow** (image processing)
- **pytesseract** (Python wrapper for Tesseract)

## Installation & Setup

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Install Tesseract-OCR
**Option A: Windows Installer (Recommended)**
- Download from: https://github.com/UB-Mannheim/tesseract/wiki
- Run the installer (default: `C:\Program Files\Tesseract-OCR`)
- The app will auto-detect it

**Option B: Portable Version**
- Download portable version
- Extract to a known location (e.g., `D:\tesseract`)
- Update Tesseract path in app Settings if not auto-detected

**Option C: With App (For EXE Distribution)**
- Place `tesseract-ocr` folder in the same directory as the exe
- The app will find it automatically

### 3. Running the Script
```bash
python Blocksoft.py
```

## Building an EXE

### Prerequisites
```bash
pip install pyinstaller
```

### Build Command
```bash
pyinstaller --onefile --windowed --icon=icon.ico Blocksoft.py
```

### Optional: Include Tesseract Portable
1. Download Tesseract portable version
2. Extract to `tesseract-ocr` folder in the project directory
3. Build with:
```bash
pyinstaller --onefile --windowed --collect-all=pytesseract --collect-all=PIL Blocksoft.py
```

## EXE Distribution Guide

### Single File EXE (Recommended)
- **Output**: `dist/Blocksoft.exe`
- **Config Location**: Same directory as exe (`Blocksoft/psg_config.json`)
- **Requirements**: User must have Tesseract installed or access to portable version

### Full Distribution Package
Include these with the exe:
- `Blocksoft.exe` (main executable)
- `tesseract-ocr/` (portable Tesseract folder)
- `README.txt` (setup instructions)

### Path Resolution (Auto-detection Order)
1. `C:\Program Files\Tesseract-OCR\tesseract.exe`
2. `C:\Program Files (x86)\Tesseract-OCR\tesseract.exe`
3. `D:\tesseract\tesseract.exe`
4. Exe directory: `Blocksoft/tesseract.exe`
5. `Blocksoft/tesseract-ocr/tesseract.exe`
6. Windows PATH environment variable

### Settings Persistence
- **Primary Location**: Same directory as exe (or script)
- **Fallback Location**: `%APPDATA%\PrivacyScreenGuard\psg_config.json`
- Settings automatically save to `psg_config.json`

## Features
✅ GUI with Start/Stop controls  
✅ Real-time screen monitoring  
✅ Adjustable keywords and blur settings  
✅ Auto cleanup of temporary files  
✅ Persistent configuration  
✅ Works as standalone EXE  
✅ Smart Tesseract detection  
✅ Fallback config location for EXE mode  

## Troubleshooting

### "Tesseract not found" warning
1. Install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki
2. Or provide portable version with exe
3. Update Tesseract path in Settings → Save

### Config not saving
- Check if exe directory is writable
- Config falls back to `%APPDATA%\PrivacyScreenGuard\`
- Check info label at bottom of app to see actual path

### PIL/Pillow errors during cleanup
- Ensure `Pillow>=9.0.0` is installed
- Run: `pip install --upgrade Pillow`

## Environment Variables
Configure via `psg_config.json` or UI:
- `check_interval`: Screen check frequency (seconds)
- `cooldown`: Pause after detection (seconds)
- `blur_radius`: Blur strength (1-60)
- `tesseract_cmd`: Path to tesseract.exe
- `cleanup_interval_hours`: Auto-cleanup frequency
- `screenshot_scale`: OCR processing scale (0.25-1.0)

## Support
For issues, check:
1. App info label (shows config & base directory)
2. Console output for error messages
3. Tesseract installation and PATH setting
