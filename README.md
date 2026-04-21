<div align="center">

<img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/Telegram-Bot_API-26A5E4?style=for-the-badge&logo=telegram&logoColor=white"/>
<img src="https://img.shields.io/badge/Windows-10%2F11-0078D6?style=for-the-badge&logo=windows&logoColor=white"/>
<img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge"/>

# 🖥️ SysTracker

### Telegram-Based Remote PC Control System

Control and monitor your Windows PC from **anywhere in the world** using Telegram on your phone.  
Supports **multiple PCs** simultaneously with seamless switching.

[Features](#-features) • [Installation](#-installation) • [Commands](#-commands) • [Multi-PC](#-multi-pc-support) • [Security](#-security) • [Build EXE](#-build-executable)

</div>

---

## 📌 Overview

SysTracker is a lightweight remote access tool that uses the **Telegram Bot API** as a communication channel. No port forwarding, no VPN, no dedicated server required. Just run the script on your PC and control it from anywhere.

```
Your Phone (Telegram)
        │
        ▼ HTTPS Encrypted
┌─────────────────────┐
│  Telegram Bot API   │
└─────────────────────┘
        │
        ▼ Long Polling
┌───────┬───────┬───────┐
│  PC1  │  PC2  │  PC3  │
│Office │ Home  │Laptop │
└───────┴───────┴───────┘
```

---

## ✨ Features

| Category | Features |
|---|---|
| 🖥️ **System** | Status, Lock, Shutdown, Restart |
| 📸 **Media** | Screenshot, Webcam (auto-deleted after send) |
| 📁 **Files** | List, Upload, Download, Delete, Search |
| 💻 **Terminal** | Run any Windows command remotely |
| 🔊 **Audio** | Volume Up/Down/Mute, Set exact %, Text-to-Speech |
| ☀️ **Display** | Get/Set screen brightness |
| 📍 **Location** | IP-based location with Google Maps link |
| 🔔 **Notifications** | Popup on screen, Ask with reply |
| 🔁 **Auto Track** | Auto location every 5 minutes |
| 🚨 **Alarm** | Remote alarm with loop |
| ☀️ **Wake Detection** | Notifies when PC wakes from sleep |
| 🤖 **Multi-PC** | Control multiple PCs from one bot |

---

## 🚀 Installation

### Method 1 — Python Script (Main PC)

**Step 1 — Clone the repository:**
```bash
git clone https://github.com/yourusername/SysTracker.git
cd SysTracker
```

**Step 2 — Install dependencies:**
```bash
pip install requests psutil pyautogui opencv-python pyttsx3 screen-brightness-control pywin32
```

**Step 3 — Configure your credentials:**

Open `tracker.py` and set:
```python
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
CHAT_ID   = "YOUR_CHAT_ID_HERE"
```

> **How to get these:**
> - Create a bot via [@BotFather](https://t.me/BotFather) on Telegram → get `BOT_TOKEN`
> - Message [@userinfobot](https://t.me/userinfobot) on Telegram → get your `CHAT_ID`

**Step 4 — Run:**
```bash
python tracker.py
```

✅ Check Telegram — you should see **"PC is Online"**

---

### Method 2 — Executable (Other PCs, No Python Needed)

**On your main PC, build the exe:**
```
Double click build.bat
→ Creates dist\tracker.exe
```

**On other PCs:**
```
1. Copy tracker.exe + install.bat to USB
2. Plug USB into other PC
3. Double click install.bat (runs as Admin automatically)
4. Check Telegram for online message ✅
```

> `install.bat` automatically:
> - Copies exe to `C:\Tools\tracker\`
> - Creates Task Scheduler entry for auto-start
> - Waits for internet before launching
> - Runs completely hidden (no terminal window)

---

## 📋 Commands

### 🖥️ System
| Command | Description |
|---|---|
| `/devices` | Show all connected PCs |
| `/status` | CPU, RAM, Battery, Uptime |
| `/lock` | Lock the PC screen |
| `/shutdown` | Shutdown PC in 5 seconds |
| `/restart` | Restart PC in 5 seconds |

### 🔊 Audio & Display
| Command | Description |
|---|---|
| `/volume up` | Increase volume 10% |
| `/volume down` | Decrease volume 10% |
| `/volume mute` | Toggle mute |
| `/vol 60` | Set exact volume (0-100) |
| `/brightness` | Get current brightness |
| `/brightness 70` | Set brightness (0-100) |
| `/say Hello` | Text to speech on PC |

### 📁 File Manager
| Command | Description |
|---|---|
| `/ls` | List current directory |
| `/ls C:\Users\Desktop` | List specific folder |
| `/upload C:\file.pdf` | Send file to Telegram |
| `/download C:\Desktop\` | Reply to file to save on PC |
| `/delete C:\file.txt` | Delete file or folder |
| `/search report C:\Users` | Search file by name |

### 📸 Media
| Command | Description |
|---|---|
| `/screenshot` | Take screenshot |
| `/webcam` | Take webcam photo |

> Both are **auto-deleted** from PC after sending to Telegram

### 💻 Terminal
| Command | Description |
|---|---|
| `/cmd ipconfig` | Network information |
| `/cmd tasklist` | Running processes |
| `/cmd systeminfo` | Full system info |
| `/cmd ping google.com` | Ping test |
| `/cmd [any command]` | Run any Windows command |

### 📍 Location & Tracking
| Command | Description |
|---|---|
| `/track` | Get location once |
| `/auto` | Auto track every 5 mins |
| `/stop` | Stop auto tracking |

### 🔔 Notifications
| Command | Description |
|---|---|
| `/notify Hello` | Show popup on PC screen |
| `/ask Are you there?` | Show input box, receive reply in Telegram |

### 🚨 Alarm
| Command | Description |
|---|---|
| `/alarm` | Start looping alarm |
| `/stop_alarm` | Stop alarm |

---

## 🖥️ Multi-PC Support

All your PCs connect to the **same bot** but only **one executes at a time**.

```
Step 1: Type /devices
        ┌─────────────────┐
        │ 🟢 PC1-Office   │
        │ 🟢 PC2-Home     │
        │ 🔴 PC3-Laptop   │
        │ 🔄 Refresh      │
        └─────────────────┘

Step 2: Tap a PC to select it
        ✅ Connected to: PC2-Home

Step 3: Use command buttons
        Commands run on PC2-Home only ✅
        PC1 and PC3 ignore all commands ✅

Step 4: Tap ⬅️ Back to switch PCs
```

### PC Status
| Status | Meaning |
|---|---|
| 🟢 Green | Online — heartbeat received in last 2 minutes |
| 🔴 Red | Offline — no heartbeat for 2+ minutes |

---

## 🔒 Security

| Layer | How It Works |
|---|---|
| **Chat ID Filter** | Only your Telegram account can send commands |
| **BOT_START_TIME** | Commands sent while PC was offline are ignored |
| **PC Selection** | Only the selected PC executes commands |
| **Reply Security** | Bot token never exposed in any external file |
| **Auto Cleanup** | Screenshots and webcam photos deleted after upload |
| **HTTPS Transport** | All communication encrypted via Telegram |

---

## 📁 Project Structure

```
SysTracker/
│
├── tracker.py          # Main bot script
├── build.bat           # Build exe using PyInstaller
├── install.bat         # Universal installer for any Windows PC
├── uninstall.bat       # Complete removal script
├── alarm.wav           # Alarm sound (optional)
└── README.md           # This file
│
├── [Auto-created]
│   ├── launcher.ps1    # Waits for internet then starts bot
│   ├── screen.png      # Screenshot (deleted after send)
│   ├── cam.png         # Webcam photo (deleted after send)
│   └── reply.vbs       # Ask reply helper (deleted after use)
```

---

## 🔧 Build Executable

Build a standalone `.exe` that works on PCs without Python:

```batch
# Make sure these are in the same folder:
# tracker.py, build.bat, alarm.wav (optional)

Double click build.bat
```

The build script includes all required hidden imports:
```batch
pyinstaller --onefile --noconsole --windowed
  --collect-all pyttsx3
  --collect-all pyautogui
  --collect-all cv2
  --collect-all comtypes
  --hidden-import=pythoncom
  --hidden-import=win32api
  ...
  tracker.py
```

Output: `dist\tracker.exe`

---

## ⚙️ Auto-Start Setup

The installer automatically configures auto-start using **Windows Task Scheduler**:

```
PC boots
    → Task Scheduler triggers (10s after login)
    → launcher.ps1 runs silently
    → Waits for internet connection
    → Launches tracker.exe
    → Bot sends "PC is Online" to Telegram ✅
```

**To manually set up auto-start:**
```
Run install.bat as Administrator
```

**To remove auto-start:**
```
Run uninstall.bat as Administrator
```

---

## 📦 Dependencies

```
requests                  HTTP communication with Telegram API
psutil                    System monitoring
pyautogui                 Screenshot capture
opencv-python             Webcam access
pyttsx3                   Text-to-speech
screen-brightness-control Screen brightness control
pywin32                   Windows API access
```

Install all at once:
```bash
pip install requests psutil pyautogui opencv-python pyttsx3 screen-brightness-control pywin32
```

---

## 🧠 How It Works

### Long Polling
The bot continuously asks Telegram for new messages every 30 seconds. No public server or webhook needed.

### Threading
Multiple background threads run simultaneously:

| Thread | Purpose |
|---|---|
| Main Thread | Command polling and routing |
| Heartbeat Thread | Keep-alive ping every 60s |
| Wake Listener | Detect PC wake from sleep |
| Auto Track | Send location every 5 mins |
| TTS Thread | Speak text without blocking |

### Retry Logic
All network requests use exponential backoff retry. If connection fails → retries with 2, 4, 8, 16, 32 second delays. Bot **never crashes** due to network issues.

---

## ⚠️ Limitations

| Limitation | Details |
|---|---|
| Windows Only | Uses Windows-specific APIs |
| 50MB Upload Limit | Telegram bot API restriction |
| IP-based Location | Not GPS accurate |
| No Live Streaming | Screenshot only, no video |
| Webcam Permission | Camera must not be in use |

---

## 🛡️ Legal & Ethical Use

> ⚠️ **Important:** This tool is designed for use on **your own PCs only**.
> Running this on someone else's computer without their knowledge or consent
> is illegal in most countries. Use responsibly.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgements

- [Telegram Bot API](https://core.telegram.org/bots/api) — Communication platform
- [psutil](https://github.com/giampaolo/psutil) — System monitoring
- [PyInstaller](https://pyinstaller.org) — Executable packaging
- [OpenCV](https://opencv.org) — Webcam capture
- [pyttsx3](https://github.com/nateshmbhat/pyttsx3) — Text to speech

---

<div align="center">

Made with ❤️ for College Project

⭐ Star this repo if you found it useful!

</div>
