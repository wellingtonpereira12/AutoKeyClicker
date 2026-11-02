"""
Window Manager for Auto Key Clicker
Enumerates top-level visible application windows, filtering out Windows background tasks and services.
"""
import ctypes
from ctypes import wintypes
import os

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
dwmapi = ctypes.windll.dwmapi

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

DWMWA_CLOAKED = 14
GW_OWNER = 4
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
GWL_EXSTYLE = -20

# System executables to ignore if they appear with generic shell titles
SYSTEM_EXES_IGNORE = {
    'shellexperiencehost.exe',
    'searchhost.exe',
    'startmenuexperiencehost.exe',
    'applicationframehost.exe',
    'systemsettings.exe',
    'lockapp.exe',
    'taskmgr.exe'  # we can keep taskmgr if needed, but usually not a game
}

IGNORED_TITLES = {
    'program manager',
    'settings',
    'configurações',
    'task view',
    'windows input experience',
    'microsoft text input application'
}

def get_process_name(pid):
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    h_proc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h_proc:
        return 'Unknown.exe'
    buffer = ctypes.create_unicode_buffer(1024)
    size = wintypes.DWORD(1024)
    res = kernel32.QueryFullProcessImageNameW(h_proc, 0, buffer, ctypes.byref(size))
    kernel32.CloseHandle(h_proc)
    if res and buffer.value:
        return os.path.basename(buffer.value)
    return 'Unknown.exe'

def is_window_cloaked(hwnd):
    cloaked = wintypes.DWORD()
    hr = dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
    if hr == 0:
        return cloaked.value != 0
    return False

def list_user_windows():
    """
    Returns a list of dicts:
    [{'hwnd': int, 'title': str, 'exe': str, 'pid': int, 'display': str}]
    Only returns real, active, user-visible top-level windows.
    """
    ensure_interactive_desktop()
    results = []

    def enum_cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value.strip()
        if not title:
            return True

        if title.lower() in IGNORED_TITLES:
            return True

        # Check cloaked (minimized UWP or virtual desktop hidden apps)
        if is_window_cloaked(hwnd):
            return True

        # Tool windows that are not app windows
        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if (ex_style & WS_EX_TOOLWINDOW) and not (ex_style & WS_EX_APPWINDOW):
            return True

        # Owned child windows (dialogs, tooltips, popup subwindows)
        owner = user32.GetWindow(hwnd, GW_OWNER)
        if owner != 0:
            return True

        # Check window size (ignore invisible 0x0 or 1x1 helper windows)
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if w <= 50 or h <= 50:
            return True

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        exe_name = get_process_name(pid.value)

        if exe_name.lower() in SYSTEM_EXES_IGNORE:
            return True

        display_name = f"[{exe_name}]  {title}"
        results.append({
            'hwnd': hwnd,
            'title': title,
            'exe': exe_name,
            'pid': pid.value,
            'display': display_name
        })
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

    # Sort games and apps alphabetically
    results.sort(key=lambda x: (x['exe'].lower(), x['title'].lower()))
    return results

def is_window_alive(hwnd):
    return bool(user32.IsWindow(hwnd))

def activate_window(hwnd):
    """Brings window to front and restores it if minimized."""
    if not is_window_alive(hwnd):
        return False
    # SW_RESTORE = 9
    user32.ShowWindow(hwnd, 9)
    user32.SetForegroundWindow(hwnd)
    return True
