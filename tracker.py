import requests
import time
import psutil
import platform
import ctypes
import ctypes.wintypes
import threading
import pyautogui
import cv2
import subprocess
import json
import os
import winsound
import pyttsx3
import pythoncom
import screen_brightness_control as sbc
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ===== CONFIG =====
BOT_TOKEN        = "YOUR_API"
CHAT_ID          = "YOUR_CHAT_ID"
BASE_URL        = f"https://api.telegram.org/bot{BOT_TOKEN}"
PC_NAME         = platform.node()
BOT_START_TIME  = time.time() - 300  # 5 min window for boot

# ===== STATE =====
auto_tracking   = False
active_devices  = {}
alarm_running   = False
SELECTED_PC     = None  # ✅ in-memory selected PC

def set_selected_pc(pc_name):
    global SELECTED_PC
    SELECTED_PC = pc_name

def is_selected():
    return SELECTED_PC == PC_NAME

# ===== ROBUST SESSION =====
def create_session():
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://",  adapter)
    return session

session = create_session()

def safe_post(url, **kwargs):
    while True:
        try:
            return session.post(url, timeout=10, **kwargs)
        except requests.exceptions.ConnectionError:
            print("⚠️ Connection lost, retrying in 10s...")
            time.sleep(10)
        except requests.exceptions.Timeout:
            print("⚠️ Timeout, retrying in 5s...")
            time.sleep(5)
        except Exception as e:
            print(f"⚠️ Request error: {e}, retrying in 10s...")
            time.sleep(10)

def safe_get(url, **kwargs):
    while True:
        try:
            return session.get(url, timeout=10, **kwargs)
        except requests.exceptions.ConnectionError:
            print("⚠️ Connection lost, retrying in 10s...")
            time.sleep(10)
        except requests.exceptions.Timeout:
            print("⚠️ Timeout, retrying in 5s...")
            time.sleep(5)
        except Exception as e:
            print(f"⚠️ Request error: {e}, retrying in 10s...")
            time.sleep(10)

# ===== SEND =====
def send_message(text):
    if len(text) > 4000:
        text = text[:4000] + "\n... (truncated)"
    safe_post(f"{BASE_URL}/sendMessage", data={
        "chat_id": CHAT_ID, "text": text
    })

def send_message_with_buttons(text, reply_markup):
    safe_post(f"{BASE_URL}/sendMessage", json={
        "chat_id": CHAT_ID,
        "text": text,
        "reply_markup": reply_markup
    })

def send_photo(path, delete_after=True):
    try:
        with open(path, "rb") as photo:
            safe_post(f"{BASE_URL}/sendPhoto",
                      data={"chat_id": CHAT_ID},
                      files={"photo": photo})
        if delete_after and os.path.exists(path):
            os.remove(path)
    except Exception as e:
        send_message(f"❌ Photo send failed: {str(e)}")

def send_document(path):
    with open(path, "rb") as doc:
        safe_post(f"{BASE_URL}/sendDocument",
                  data={"chat_id": CHAT_ID},
                  files={"document": doc})

def edit_message(chat_id, message_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    safe_post(f"{BASE_URL}/editMessageText", json=data)

# ===== TERMINAL =====
def run_terminal_command(command):
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True,
            text=True, timeout=30
        )
        output = ""
        if result.stdout:
            output += f"✅ Output:\n{result.stdout}"
        if result.stderr:
            output += f"\n⚠️ Error:\n{result.stderr}"
        if not result.stdout and not result.stderr:
            output = "✅ Command executed (no output)"
        if result.returncode != 0:
            output += f"\n\n⚠️ Return code: {result.returncode}"
        return output
    except subprocess.TimeoutExpired:
        return "❌ Command timed out (30s limit)"
    except Exception as e:
        return f"❌ Error: {str(e)}"

# ===== TEXT TO SPEECH =====
def say_text(text):
    try:
        pythoncom.CoInitialize()
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 1.0)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
        pythoncom.CoUninitialize()
        send_message(f"🗣 Said: {text}")
    except Exception as e:
        send_message(f"❌ TTS failed: {str(e)}")

# ===== SCREEN NOTIFICATIONS =====
def show_popup(text):
    try:
        subprocess.Popen(
            f'powershell -c "Add-Type -AssemblyName System.Windows.Forms;'
            f'[System.Windows.Forms.MessageBox]::Show(\'{text}\',\'PC Remote Bot\')"',
            shell=True
        )
        send_message(f"✅ Popup shown on {PC_NAME}")
    except Exception as e:
        send_message(f"❌ Popup failed: {str(e)}")

def show_toast_with_reply(text):
    try:
        import re
        import http.server
        import urllib.parse
        import socket

        clean_text = re.sub(r'[^\x00-\x7F]+', '', text).strip()
        reply_received = [None]

        class ReplyHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                query = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query)
                if "reply" in params:
                    reply_received[0] = params["reply"][0]
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
            def log_message(self, format, *args):
                pass

        s = socket.socket()
        s.bind(("", 0))
        port = s.getsockname()[1]
        s.close()

        server = http.server.HTTPServer(("localhost", port), ReplyHandler)

        vbs_content = f"""
Dim reply
reply = InputBox("{clean_text}", "PC Remote Bot - Reply")
If reply <> "" Then
    Dim http
    Set http = CreateObject("MSXML2.XMLHTTP")
    http.Open "GET", "http://localhost:{port}/?reply=" & reply, False
    http.Send
End If
"""
        vbs_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "reply.vbs"
        )
        with open(vbs_path, "w", encoding="ascii", errors="ignore") as f:
            f.write(vbs_content)

        subprocess.Popen(["wscript.exe", vbs_path])
        send_message(f"✅ Reply box shown on {PC_NAME}\nWaiting for reply...")

        server.timeout = 30
        server.handle_request()

        if reply_received[0]:
            send_message(f"💬 Reply from {PC_NAME}:\n{reply_received[0]}")
        else:
            send_message(f"⏰ No reply received from {PC_NAME}")

        if os.path.exists(vbs_path):
            os.remove(vbs_path)

    except Exception as e:
        send_message(f"❌ Failed: {str(e)}")

# ===== POWER =====
def shutdown_pc():
    try:
        send_message("🔴 Shutting down in 5 seconds...")
        time.sleep(1)
        subprocess.run("shutdown /s /t 5", shell=True)
    except Exception as e:
        send_message(f"❌ Shutdown failed: {str(e)}")

def restart_pc():
    try:
        send_message("🔄 Restarting in 5 seconds...")
        time.sleep(1)
        subprocess.run("shutdown /r /t 5", shell=True)
    except Exception as e:
        send_message(f"❌ Restart failed: {str(e)}")

def lock_pc():
    try:
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
        send_message("🔒 PC Locked")
    except Exception as e:
        send_message(f"❌ Lock failed: {str(e)}")

# ===== VOLUME =====
def volume_up():
    try:
        subprocess.run(
            'powershell -c "(New-Object -comObject WScript.Shell).SendKeys([char]175)"',
            shell=True
        )
        send_message("🔊 Volume increased")
    except Exception as e:
        send_message(f"❌ Volume error: {str(e)}")

def volume_down():
    try:
        subprocess.run(
            'powershell -c "(New-Object -comObject WScript.Shell).SendKeys([char]174)"',
            shell=True
        )
        send_message("🔉 Volume decreased")
    except Exception as e:
        send_message(f"❌ Volume error: {str(e)}")

def volume_mute():
    try:
        subprocess.run(
            'powershell -c "(New-Object -comObject WScript.Shell).SendKeys([char]173)"',
            shell=True
        )
        send_message("🔇 Volume mute toggled")
    except Exception as e:
        send_message(f"❌ Mute error: {str(e)}")

def volume_set(level):
    try:
        level = max(0, min(100, int(level)))
        script = f"""
$code = @"
using System.Runtime.InteropServices;
[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"),
 InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioEndpointVolume {{
    int f(); int g(); int h(); int i();
    int SetMasterVolumeLevelScalar(float fLevel, System.Guid pguidEventContext);
    int j();
    int GetMasterVolumeLevelScalar(out float pfLevel);
    int k(); int l(); int m(); int n();
    int SetMute([MarshalAs(UnmanagedType.Bool)] bool bMute, System.Guid pguidEventContext);
    int GetMute(out bool pbMute);
}}
[Guid("D666063F-1587-4E43-81F1-B948E807363F"),
 InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice {{
    int Activate(ref System.Guid id, uint ctx, System.IntPtr parms,
    [MarshalAs(UnmanagedType.IUnknown)] out object ppInterface);
}}
[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"),
 InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator {{
    int f();
    int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice ppDevice);
}}
[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
class MMDeviceEnumeratorClass {{}}
public class AudioManager {{
    public static void SetVolume(float level) {{
        var enumerator = (IMMDeviceEnumerator)(new MMDeviceEnumeratorClass());
        IMMDevice device;
        enumerator.GetDefaultAudioEndpoint(0, 1, out device);
        var iid = typeof(IAudioEndpointVolume).GUID;
        object o;
        device.Activate(ref iid, 23, System.IntPtr.Zero, out o);
        var ep = (IAudioEndpointVolume)o;
        ep.SetMasterVolumeLevelScalar({level / 100.0}f, System.Guid.Empty);
    }}
}}
"@
Add-Type -TypeDefinition $code
[AudioManager]::SetVolume({level / 100.0})
Write-Output "OK"
"""
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True, text=True, timeout=15
        )
        if "OK" in result.stdout:
            send_message(f"🔊 Volume set to {level}%")
        else:
            send_message(f"❌ Failed: {result.stderr.strip()[:200]}")
    except subprocess.TimeoutExpired:
        send_message("❌ Volume command timed out")
    except Exception as e:
        send_message(f"❌ Volume error: {str(e)}")

# ===== BRIGHTNESS =====
def set_brightness(level):
    try:
        level = max(0, min(100, int(level)))
        sbc.set_brightness(level)
        send_message(f"☀️ Brightness set to {level}%")
    except Exception as e:
        send_message(f"❌ Brightness error: {str(e)}")

def get_brightness():
    try:
        level = sbc.get_brightness()
        send_message(f"☀️ Current brightness: {level[0]}%")
    except Exception as e:
        send_message(f"❌ Brightness error: {str(e)}")

# ===== FILE MANAGER =====
def list_files(path):
    try:
        if not path:
            path = os.getcwd()
        items = os.listdir(path)
        output = f"📁 {path}\n\n"
        folders, files = [], []
        for item in items:
            full = os.path.join(path, item)
            if os.path.isdir(full):
                folders.append(f"📂 {item}/")
            else:
                size = os.path.getsize(full)
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size//1024} KB"
                else:
                    size_str = f"{size//1024//1024} MB"
                files.append(f"📄 {item} ({size_str})")
        output += "\n".join(folders + files)
        if not items:
            output += "(empty folder)"
        send_message(output)
    except PermissionError:
        send_message(f"❌ Permission denied: {path}")
    except FileNotFoundError:
        send_message(f"❌ Path not found: {path}")
    except Exception as e:
        send_message(f"❌ Error: {str(e)}")

def upload_file(path):
    try:
        if not os.path.exists(path):
            send_message(f"❌ File not found: {path}")
            return
        size = os.path.getsize(path)
        if size > 50 * 1024 * 1024:
            send_message("❌ File too large (max 50MB)")
            return
        send_message(f"📤 Uploading: {os.path.basename(path)}...")
        send_document(path)
        send_message("✅ Upload complete!")
    except Exception as e:
        send_message(f"❌ Upload failed: {str(e)}")

def delete_file(path):
    try:
        if not os.path.exists(path):
            send_message(f"❌ Not found: {path}")
            return
        if os.path.isdir(path):
            import shutil
            shutil.rmtree(path)
            send_message(f"🗑 Deleted folder: {path}")
        else:
            os.remove(path)
            send_message(f"🗑 Deleted file: {path}")
    except PermissionError:
        send_message(f"❌ Permission denied: {path}")
    except Exception as e:
        send_message(f"❌ Delete failed: {str(e)}")

def search_files(filename, search_path="C:\\"):
    try:
        send_message(f"🔍 Searching '{filename}' in {search_path}...")
        results = []
        for root, dirs, files in os.walk(search_path):
            dirs[:] = [d for d in dirs if d not in [
                'Windows', '$Recycle.Bin', 'System Volume Information'
            ]]
            for file in files:
                if filename.lower() in file.lower():
                    results.append(os.path.join(root, file))
                if len(results) >= 20:
                    break
            if len(results) >= 20:
                break
        if results:
            output = f"🔍 Found {len(results)} result(s):\n\n" + "\n".join(results)
            if len(results) == 20:
                output += "\n\n⚠️ Showing first 20 only"
        else:
            output = f"❌ No files found: '{filename}'"
        send_message(output)
    except Exception as e:
        send_message(f"❌ Search failed: {str(e)}")

def download_file_from_telegram(file_id, save_path):
    try:
        res = safe_get(f"{BASE_URL}/getFile",
                       params={"file_id": file_id}).json()
        file_path = res["result"]["file_path"]
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        file_data = safe_get(url).content
        if os.path.isdir(save_path):
            filename = file_path.split("/")[-1]
            save_path = os.path.join(save_path, filename)
        with open(save_path, "wb") as f:
            f.write(file_data)
        send_message(f"✅ Saved to: {save_path}")
    except Exception as e:
        send_message(f"❌ Download failed: {str(e)}")

# ===== LOCATION =====
def get_location():
    try:
        ip   = safe_get("https://api.ipify.org").text
        data = safe_get(f"http://ip-api.com/json/{ip}").json()
        lat, lon = data.get("lat"), data.get("lon")
        return f"""📍 {data.get("city")}, {data.get("regionName")}, {data.get("country")}
🌐 IP: {ip}
🗺 https://maps.google.com/?q={lat},{lon}"""
    except Exception as e:
        return f"❌ Location error: {str(e)}"

# ===== STATUS =====
def get_status():
    try:
        uptime  = time.time() - psutil.boot_time()
        mins    = int(uptime // 60)
        battery = psutil.sensors_battery()
        batt    = f"{battery.percent}%" if battery else "N/A"
        return f"""💻 {platform.node()}
🧠 CPU:     {psutil.cpu_percent()}%
🧬 RAM:     {psutil.virtual_memory().percent}%
🔋 Battery: {batt}
⏱ Uptime:  {mins} min"""
    except Exception as e:
        return f"❌ Status error: {str(e)}"

# ===== SCREENSHOT / WEBCAM =====
def take_screenshot():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screen.png")
    pyautogui.screenshot(path)
    return path

def take_webcam():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cam.png")
    cam = cv2.VideoCapture(0)
    ret, frame = cam.read()
    if ret:
        cv2.imwrite(path, frame)
    cam.release()
    return path

# ===== ALARM =====
def play_alarm():
    global alarm_running
    alarm_running = True
    alarm_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "alarm.wav"
    )
    if os.path.exists(alarm_path):
        winsound.PlaySound(alarm_path,
                           winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
    else:
        winsound.PlaySound("SystemExclamation",
                           winsound.SND_ALIAS | winsound.SND_ASYNC | winsound.SND_LOOP)

def stop_alarm():
    global alarm_running
    alarm_running = False
    winsound.PlaySound(None, winsound.SND_PURGE)

# ===== AUTO TRACK =====
def auto_track():
    global auto_tracking
    while auto_tracking:
        send_message(get_location())
        time.sleep(300)

# ===== WAKE FROM SLEEP DETECTION =====
def listen_for_wake():
    WM_POWERBROADCAST      = 0x0218
    PBT_APMRESUMEAUTOMATIC = 0x0012
    PBT_APMRESUMESUSPEND   = 0x0007

    WNDPROCTYPE = ctypes.WINFUNCTYPE(
        ctypes.c_int64,
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_int64,
        ctypes.c_int64
    )

    def wnd_proc(hwnd, msg, wparam, lparam):
        try:
            if msg == WM_POWERBROADCAST:
                if wparam in (PBT_APMRESUMEAUTOMATIC, PBT_APMRESUMESUSPEND):
                    send_message(f"☀️ {PC_NAME} woke from sleep!")
                    active_devices[PC_NAME] = time.time()
        except Exception as e:
            print(f"⚠️ wnd_proc error: {e}")
        return ctypes.windll.user32.DefWindowProcW(
            ctypes.c_void_p(hwnd),
            ctypes.c_uint(msg),
            ctypes.c_int64(wparam),
            ctypes.c_int64(lparam)
        )

    wnd_proc_ptr = WNDPROCTYPE(wnd_proc)

    class WNDCLASS(ctypes.Structure):
        _fields_ = [
            ("style",         ctypes.c_uint),
            ("lpfnWndProc",   ctypes.c_void_p),
            ("cbClsExtra",    ctypes.c_int),
            ("cbWndExtra",    ctypes.c_int),
            ("hInstance",     ctypes.c_void_p),
            ("hIcon",         ctypes.c_void_p),
            ("hCursor",       ctypes.c_void_p),
            ("hbrBackground", ctypes.c_void_p),
            ("lpszMenuName",  ctypes.c_wchar_p),
            ("lpszClassName", ctypes.c_wchar_p),
        ]

    ctypes.windll.user32.DefWindowProcW.restype  = ctypes.c_int64
    ctypes.windll.user32.DefWindowProcW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_int64,
        ctypes.c_int64
    ]

    hinstance = ctypes.windll.kernel32.GetModuleHandleW(None)
    wc = WNDCLASS()
    wc.lpfnWndProc   = ctypes.cast(wnd_proc_ptr, ctypes.c_void_p)
    wc.hInstance     = hinstance
    wc.lpszClassName = "BotWakeListener"
    ctypes.windll.user32.RegisterClassW(ctypes.byref(wc))
    hwnd = ctypes.windll.user32.CreateWindowExW(
        0, "BotWakeListener", "BotWakeListener",
        0, 0, 0, 0, 0, None, None, hinstance, None
    )
    if not hwnd:
        print("⚠️ Wake listener window creation failed")
        return
    print("✅ Wake listener started")
    msg_struct = ctypes.wintypes.MSG()
    while True:
        ret = ctypes.windll.user32.GetMessageW(
            ctypes.byref(msg_struct), None, 0, 0
        )
        if ret == 0 or ret == -1:
            break
        ctypes.windll.user32.TranslateMessage(ctypes.byref(msg_struct))
        ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg_struct))

# ===== DEVICE REGISTRY =====
def heartbeat():
    while True:
        active_devices[PC_NAME] = time.time()
        time.sleep(60)

def register_device():
    active_devices[PC_NAME] = time.time()
    send_message_with_buttons(f"✅ {PC_NAME} is Online", build_device_keyboard())
    threading.Thread(target=heartbeat, daemon=True).start()

# ===== KEYBOARDS =====
def build_device_keyboard():
    buttons = []
    for name, last_seen in active_devices.items():
        status = "🟢" if time.time() - last_seen < 120 else "🔴"
        buttons.append([{
            "text": f"{status} {name}",
            "callback_data": f"select_{name}"
        }])
    buttons.append([{"text": "🔄 Refresh", "callback_data": "refresh_devices"}])
    return {"inline_keyboard": buttons}

def build_commands_keyboard(pc_name):
    return {
        "inline_keyboard": [
            [
                {"text": "📊 Status",     "callback_data": "cmd_status"},
                {"text": "📍 Location",   "callback_data": "cmd_track"}
            ],
            [
                {"text": "📸 Screenshot", "callback_data": "cmd_screenshot"},
                {"text": "📷 Webcam",     "callback_data": "cmd_webcam"}
            ],
            [
                {"text": "🔒 Lock",       "callback_data": "cmd_lock"},
                {"text": "🔊 Alarm",      "callback_data": "cmd_alarm"}
            ],
            [
                {"text": "🔴 Shutdown",   "callback_data": "cmd_shutdown"},
                {"text": "🔄 Restart",    "callback_data": "cmd_restart"}
            ],
            [
                {"text": "🔉 Vol -",      "callback_data": "cmd_vol_down"},
                {"text": "🔇 Mute",       "callback_data": "cmd_vol_mute"},
                {"text": "🔊 Vol +",      "callback_data": "cmd_vol_up"},
                {"text": "🎚 Set Vol",    "callback_data": "cmd_vol_set"}
            ],
            [
                {"text": "☀️ Brightness", "callback_data": "cmd_brightness"},
                {"text": "🗣 Say",        "callback_data": "cmd_say"}
            ],
            [
                {"text": "💬 Popup",      "callback_data": "cmd_popup"},
                {"text": "❓ Ask",        "callback_data": "cmd_ask"}
            ],
            [
                {"text": "💻 Terminal",   "callback_data": "cmd_terminal"},
                {"text": "📁 Files",      "callback_data": "cmd_files"}
            ],
            [
                {"text": "🔁 Auto Track", "callback_data": "cmd_auto"},
                {"text": "🛑 Stop All",   "callback_data": "cmd_stop"}
            ],
            [{"text": "⬅️ Back",          "callback_data": "show_devices"}]
        ]
    }

# ===== HANDLE CALLBACK =====
def handle_callback(callback):
    global auto_tracking
    query_id   = callback["id"]
    data       = callback["data"]
    chat_id    = str(callback["message"]["chat"]["id"])
    message_id = callback["message"]["message_id"]

    # ✅ Ignore old commands sent before bot started
    msg_time = callback["message"].get("date", 0)
    if msg_time < BOT_START_TIME:
        safe_post(f"{BASE_URL}/answerCallbackQuery", data={
            "callback_query_id": query_id,
            "text": "⏰ Command ignored (sent while PC was offline)",
            "show_alert": True
        })
        return

    if chat_id != CHAT_ID:
        return

    safe_post(f"{BASE_URL}/answerCallbackQuery",
              data={"callback_query_id": query_id})

    # ===== DEVICE SELECTION — runs on ALL PCs =====
    if data in ("show_devices", "refresh_devices"):
        active_devices[PC_NAME] = time.time()
        edit_message(chat_id, message_id,
                     "🖥 Select a Device:", build_device_keyboard())
        return

    elif data.startswith("select_"):
        selected = data.replace("select_", "")
        set_selected_pc(selected)
        edit_message(chat_id, message_id,
                     f"✅ Connected to: {selected}\nChoose a command:",
                     build_commands_keyboard(selected))
        return

    # ✅ Only selected PC runs commands
    if not is_selected():
        safe_post(f"{BASE_URL}/answerCallbackQuery", data={
            "callback_query_id": query_id,
            "text": "⚠️ Please select this PC first using /devices",
            "show_alert": True
        })
        return

    # ===== COMMANDS =====
    if   data == "cmd_status":      send_message(get_status())
    elif data == "cmd_track":       send_message(get_location())
    elif data == "cmd_screenshot":  send_photo(take_screenshot())
    elif data == "cmd_webcam":      send_photo(take_webcam())
    elif data == "cmd_lock":        lock_pc()
    elif data == "cmd_shutdown":    shutdown_pc()
    elif data == "cmd_restart":     restart_pc()
    elif data == "cmd_vol_up":      volume_up()
    elif data == "cmd_vol_down":    volume_down()
    elif data == "cmd_vol_mute":    volume_mute()
    elif data == "cmd_alarm":
        play_alarm()
        send_message("🔊 Alarm started")
    elif data == "cmd_brightness":
        get_brightness()
        send_message("To set: /brightness 70")
    elif data == "cmd_say":
        send_message("🗣 Usage: /say <text>\nExample: /say Hello World")
    elif data == "cmd_popup":
        send_message("💬 Usage: /notify <text>\nExample: /notify Hello World")
    elif data == "cmd_ask":
        send_message("❓ Usage: /ask <question>\nExample: /ask Are you there?")
    elif data == "cmd_vol_set":
        send_message("🎚 Set volume:\n/vol 0   - Mute\n/vol 25  - 25%\n/vol 50  - 50%\n/vol 75  - 75%\n/vol 100 - Max")
    elif data == "cmd_terminal":
        send_message("💻 Usage: /cmd <command>\nExample: /cmd ipconfig")
    elif data == "cmd_files":
        username = os.environ.get("USERNAME", "User")
        send_message(f"""📁 FILE MANAGER GUIDE
══════════════════════

📋 LIST FILES
/ls
/ls C:\\Users\\{username}\\Desktop
/ls C:\\Users\\{username}\\Documents

📤 UPLOAD  (PC → Telegram)
/upload C:\\Users\\{username}\\Desktop\\photo.jpg
/upload C:\\Users\\{username}\\Documents\\file.pdf

📥 DOWNLOAD  (Telegram → PC)
1. Send any file to this chat
2. REPLY to that file with:
/download C:\\Users\\{username}\\Desktop\\
/download C:\\Users\\{username}\\Downloads\\

🗑 DELETE
/delete C:\\Users\\{username}\\Desktop\\file.txt
/delete C:\\Users\\{username}\\Desktop\\folder

🔍 SEARCH
/search photo.jpg
/search report C:\\Users\\{username}
/search .pdf C:\\Users\\{username}\\Documents

💡 TIPS
- Use /ls first to see file names
- /download must be a REPLY to a file
- Max upload size is 50MB
══════════════════════""")
    elif data == "cmd_stop":
        auto_tracking = False
        stop_alarm()
        send_message("🛑 All stopped")
    elif data == "cmd_auto":
        if not auto_tracking:
            auto_tracking = True
            threading.Thread(target=auto_track, daemon=True).start()
            send_message("🔁 Auto tracking ON")
        else:
            send_message("Already running")

# ===== GET UPDATES =====
def get_updates(offset=None):
    return safe_get(f"{BASE_URL}/getUpdates", params={
        "timeout": 30, "offset": offset
    }).json()

# ===== MAIN =====
def main():
    global auto_tracking
    last_update_id = None

    register_device()
    threading.Thread(target=listen_for_wake, daemon=True).start()

    while True:
        try:
            updates = get_updates(last_update_id)

            for u in updates.get("result", []):
                last_update_id = u["update_id"] + 1

                try:
                    if "callback_query" in u:
                        handle_callback(u["callback_query"])
                        continue

                    msg      = u.get("message", {})
                    chat_id  = str(msg.get("chat", {}).get("id"))
                    text     = msg.get("text", "") or ""
                    msg_time = msg.get("date", 0)

                    if chat_id != CHAT_ID:
                        continue

                    # ✅ Skip old commands
                    if msg_time < BOT_START_TIME:
                        print(f"⏰ Ignoring old command: {text}")
                        continue

                    # ✅ Skip if not selected PC
                    # (except global commands)
                    if text not in ("/devices", "/start", "/help"):
                        if not is_selected():
                            send_message(f"⚠️ Please select a PC first using /devices")
                            continue

                    # ===== SAY =====
                    if text.startswith("/say "):
                        threading.Thread(
                            target=say_text,
                            args=(text[5:].strip(),),
                            daemon=True
                        ).start()

                    # ===== NOTIFICATIONS =====
                    elif text.startswith("/notify "):
                        msg_text = text[8:].strip()
                        if msg_text:
                            threading.Thread(
                                target=show_popup, args=(msg_text,), daemon=True
                            ).start()
                        else:
                            send_message("❌ Usage: /notify <text>")

                    elif text.startswith("/ask "):
                        msg_text = text[5:].strip()
                        if msg_text:
                            threading.Thread(
                                target=show_toast_with_reply,
                                args=(msg_text,),
                                daemon=True
                            ).start()
                        else:
                            send_message("❌ Usage: /ask <question>")

                    # ===== POWER =====
                    elif text == "/shutdown": shutdown_pc()
                    elif text == "/restart":  restart_pc()

                    # ===== VOLUME =====
                    elif text == "/volume up":   volume_up()
                    elif text == "/volume down": volume_down()
                    elif text == "/volume mute": volume_mute()
                    elif text.startswith("/volume "):
                        volume_set(text.split(" ")[1])
                    elif text.startswith("/vol "):
                        try:
                            level = int(text.split(" ")[1])
                            if 0 <= level <= 100:
                                volume_set(level)
                            else:
                                send_message("❌ Enter 0-100\nExample: /vol 80")
                        except ValueError:
                            send_message("❌ Usage: /vol 60")

                    # ===== BRIGHTNESS =====
                    elif text == "/brightness":
                        get_brightness()
                    elif text.startswith("/brightness "):
                        set_brightness(text.split(" ")[1])

                    # ===== FILE MANAGER =====
                    elif text.startswith("/ls"):
                        list_files(text[3:].strip() or os.getcwd())

                    elif text.startswith("/upload "):
                        threading.Thread(
                            target=upload_file,
                            args=(text[8:].strip(),),
                            daemon=True
                        ).start()

                    elif text.startswith("/delete "):
                        delete_file(text[8:].strip())

                    elif text.startswith("/search "):
                        parts = text[8:].strip().split(" ", 1)
                        threading.Thread(
                            target=search_files,
                            args=(parts[0], parts[1] if len(parts) > 1 else "C:\\"),
                            daemon=True
                        ).start()

                    elif text.startswith("/download"):
                        save_path = text[9:].strip() or os.getcwd()
                        reply = msg.get("reply_to_message", {})
                        doc   = reply.get("document") or reply.get("photo", [{}])[-1]
                        if doc:
                            threading.Thread(
                                target=download_file_from_telegram,
                                args=(doc.get("file_id"), save_path),
                                daemon=True
                            ).start()
                        else:
                            send_message("❌ Reply to a file with /download <path>")

                    # ===== TERMINAL =====
                    elif text.startswith("/cmd "):
                        command = text[5:].strip()
                        send_message(f"⚙️ Running on {PC_NAME}: {command}")
                        result = run_terminal_command(command)
                        send_message(f"💻 [{PC_NAME}]\n{result}")
                    elif text == "/cmd":
                        send_message("❌ Usage: /cmd <command>")

                    # ===== DEVICES =====
                    elif text == "/devices":
                        active_devices[PC_NAME] = time.time()
                        send_message_with_buttons(
                            "🖥 Select a Device:", build_device_keyboard()
                        )

                    # ===== ORIGINAL COMMANDS =====
                    elif text == "/track":      send_message(get_location())
                    elif text == "/status":     send_message(get_status())
                    elif text == "/lock":       lock_pc()
                    elif text == "/screenshot": send_photo(take_screenshot())
                    elif text == "/webcam":     send_photo(take_webcam())
                    elif text == "/alarm":
                        play_alarm()
                        send_message("🔊 Alarm started")
                    elif text == "/stop_alarm":
                        stop_alarm()
                        send_message("🛑 Alarm stopped")
                    elif text == "/auto":
                        if not auto_tracking:
                            auto_tracking = True
                            threading.Thread(
                                target=auto_track, daemon=True
                            ).start()
                            send_message("🔁 Auto tracking ON")
                    elif text == "/stop":
                        auto_tracking = False
                        send_message("🛑 Tracking OFF")

                    elif text in ("/start", "/help"):
                        send_message(f"""📌 Commands — {PC_NAME}

🖥 System:
/devices              - Show all PCs
/status               - System info
/lock                 - Lock PC
/shutdown             - Shutdown
/restart              - Restart

🔊 Audio & Display:
/volume up/down/mute  - Volume control
/vol 60               - Set volume to 60%
/brightness           - Get brightness
/brightness 70        - Set brightness 70%
/say <text>           - Text to speech

🔔 Notifications:
/notify <text>        - Show popup on screen
/ask <question>       - Show popup and get reply

📁 Files:
/ls <path>            - List files
/upload <path>        - Upload to Telegram
/download <path>      - Reply to file to save
/delete <path>        - Delete file or folder
/search <name> <path> - Search file

📸 Media:
/screenshot           - Screenshot
/webcam               - Webcam photo

💻 Terminal:
/cmd <command>        - Run any command

📍 Location:
/track                - Get location
/auto                 - Auto tracking
/stop                 - Stop tracking

🔊 Alarm:
/alarm                - Start alarm
/stop_alarm           - Stop alarm""")

                except Exception as e:
                    print(f"⚠️ Message error: {e}")
                    continue

        except Exception as e:
            print(f"⚠️ Main loop error: {e}, restarting in 5s...")
            time.sleep(5)
            continue

        time.sleep(2)

main()