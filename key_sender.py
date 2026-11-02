"""
Key Sender Module
Provides robust keystroke injection for both background (PostMessage) and foreground (SendInput) modes.
Compatible with DirectX, DirectInput, OpenGL, and standard Windows applications.
"""
import ctypes
from ctypes import wintypes
import time

user32 = ctypes.windll.user32

# Ensure connection to interactive desktop
def ensure_interactive_desktop():
    try:
        hwinsta = user32.OpenWindowStationW('WinSta0', False, 0x10000000)
        if hwinsta:
            user32.SetProcessWindowStation(hwinsta)
            hdesk = user32.OpenDesktopW('Default', 0, False, 0x10000000)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
    except Exception:
        pass

ensure_interactive_desktop()

# Windows Constants
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_CHAR = 0x0102
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205

INPUT_KEYBOARD = 1
INPUT_MOUSE = 0
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

# Standard Virtual Key dictionary
KEY_MAP = {
    # Function Keys
    'F1': 0x70, 'F2': 0x71, 'F3': 0x72, 'F4': 0x73,
    'F5': 0x74, 'F6': 0x75, 'F7': 0x76, 'F8': 0x77,
    'F9': 0x78, 'F10': 0x79, 'F11': 0x7A, 'F12': 0x7B,
    
    # Numbers
    '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
    '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,

    # Numpad
    'NUMPAD0': 0x60, 'NUMPAD1': 0x61, 'NUMPAD2': 0x62, 'NUMPAD3': 0x63,
    'NUMPAD4': 0x64, 'NUMPAD5': 0x65, 'NUMPAD6': 0x66, 'NUMPAD7': 0x67,
    'NUMPAD8': 0x68, 'NUMPAD9': 0x69,

    # Common Action Keys
    'SPACE': 0x20, 'ESPAÇO': 0x20,
    'ENTER': 0x0D,
    'TAB': 0x09,
    'ESC': 0x1B,
    'BACKSPACE': 0x08,
    'SHIFT': 0x10,
    'CTRL': 0x11,
    'ALT': 0x12,
    'INSERT': 0x2D,
    'DELETE': 0x2E,
    'HOME': 0x24,
    'END': 0x23,
    'PAGE_UP': 0x21, 'PGUP': 0x21,
    'PAGE_DOWN': 0x22, 'PGDN': 0x22,
    'PAUSE': 0x13,
    'SCROLL_LOCK': 0x91,
    'CAPSLOCK': 0x14,
    'TILDE': 0xC0, '`': 0xC0,

    # Arrows
    'UP': 0x26, 'DOWN': 0x28, 'LEFT': 0x25, 'RIGHT': 0x27,

    # Mouse
    'MOUSE_LEFT': 0x01,
    'MOUSE_RIGHT': 0x02,
}

# Add Letters A-Z
for ch in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
    KEY_MAP[ch] = ord(ch)

# Ctypes structures for SendInput
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong)
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong)
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD)
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT)
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", INPUT_UNION)
    ]

def resolve_key(key_str):
    """
    Resolves a string key (like 'F10', 'f10', '1', 'space', 'a') to virtual key code and scancode.
    Returns (vk, scancode).
    """
    s = key_str.strip().upper()
    if s in KEY_MAP:
        vk = KEY_MAP[s]
    elif len(s) == 1:
        # Check standard character
        vk = ord(s)
    else:
        # Fallback to F10 if unrecognized
        vk = 0x79

    scancode = user32.MapVirtualKeyW(vk, 0)
    return vk, scancode

def send_key_background(hwnd, key_str, hold_ms=35):
    """
    Sends a keystroke directly to a window handle in the BACKGROUND.
    Does not steal focus or move the cursor!
    """
    ensure_interactive_desktop()
    if not user32.IsWindow(hwnd):
        return False

    vk, scancode = resolve_key(key_str)

    # Check for mouse actions
    if key_str.upper() in ('MOUSE_LEFT', 'CLIQUE_ESQUERDO'):
        user32.PostMessageW(hwnd, WM_LBUTTONDOWN, 0x0001, 0)
        time.sleep(hold_ms / 1000.0)
        user32.PostMessageW(hwnd, WM_LBUTTONUP, 0x0000, 0)
        return True

    if key_str.upper() in ('MOUSE_RIGHT', 'CLIQUE_DIREITO'):
        user32.PostMessageW(hwnd, WM_RBUTTONDOWN, 0x0002, 0)
        time.sleep(hold_ms / 1000.0)
        user32.PostMessageW(hwnd, WM_RBUTTONUP, 0x0000, 0)
        return True

    # Windows lParam packing:
    # Bits 0-15: Repeat count (1)
    # Bits 16-23: Scan code
    # Bit 24: Extended key flag (1 for extended keys like Insert, Delete, arrows)
    # Bit 29: Context code (0)
    # Bit 30: Previous key state (0 for down, 1 for up)
    # Bit 31: Transition state (0 for down, 1 for up)
    ext_flag = (1 << 24) if vk in (0x2D, 0x2E, 0x24, 0x23, 0x21, 0x22, 0x26, 0x28, 0x25, 0x27) else 0
    lparam_down = 1 | (scancode << 16) | ext_flag
    lparam_up = 1 | (scancode << 16) | ext_flag | (1 << 30) | (1 << 31)

    user32.PostMessageW(hwnd, WM_KEYDOWN, vk, lparam_down)
    time.sleep(hold_ms / 1000.0)
    user32.PostMessageW(hwnd, WM_KEYUP, vk, lparam_up)
    return True

def send_key_foreground(key_str, hold_ms=35):
    """
    Sends a keystroke using SendInput with DirectInput scan codes.
    Compatible with games running in exclusive fullscreen or strict DirectInput.
    """
    vk, scancode = resolve_key(key_str)

    # Down input
    inp_down = INPUT()
    inp_down.type = INPUT_KEYBOARD
    inp_down.u.ki.wVk = 0  # 0 when using KEYEVENTF_SCANCODE for DirectX compatibility
    inp_down.u.ki.wScan = scancode
    inp_down.u.ki.dwFlags = KEYEVENTF_SCANCODE
    inp_down.u.ki.time = 0
    inp_down.u.ki.dwExtraInfo = 0

    user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))
    time.sleep(hold_ms / 1000.0)

    # Up input
    inp_up = INPUT()
    inp_up.type = INPUT_KEYBOARD
    inp_up.u.ki.wVk = 0
    inp_up.u.ki.wScan = scancode
    inp_up.u.ki.dwFlags = KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP
    inp_up.u.ki.time = 0
    inp_up.u.ki.dwExtraInfo = 0

    user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))
    return True
