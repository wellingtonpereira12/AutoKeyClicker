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

# Explicit Win32 64-bit signatures to prevent pointer truncation & access violations
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetForegroundWindow.argtypes = []
user32.GetAncestor.restype = wintypes.HWND
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetWindow.restype = wintypes.HWND
user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
user32.IsWindow.restype = wintypes.BOOL
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.ShowWindow.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]

_desktop_ensured = False

# Ensure connection to interactive desktop (run once safely)
def ensure_interactive_desktop():
    global _desktop_ensured
    if _desktop_ensured:
        return
    try:
        hwinsta = user32.OpenWindowStationW('WinSta0', False, 0x10000000)
        if hwinsta:
            user32.SetProcessWindowStation(hwinsta)
            hdesk = user32.OpenDesktopW('Default', 0, False, 0x10000000)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
        _desktop_ensured = True
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
        if owner:
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
        if pid.value == kernel32.GetCurrentProcessId():
            return True

        exe_name = get_process_name(pid.value)

        if exe_name.lower() in SYSTEM_EXES_IGNORE or exe_name.lower() == 'autokeyclicker.exe':
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
    if not hwnd:
        return False
    return bool(user32.IsWindow(hwnd))

def is_target_window_active(target_hwnd):
    """
    Returns True if target_hwnd (or a child/popup belonging to the same process)
    is currently the active foreground window.
    """
    if not target_hwnd or not is_window_alive(target_hwnd):
        return False
    try:
        fg_hwnd = user32.GetForegroundWindow()
        if not fg_hwnd:
            return False
        if fg_hwnd == target_hwnd:
            return True
        # Check parent / root ancestor
        # GA_ROOT = 2, GA_ROOTOWNER = 3
        if user32.GetAncestor(fg_hwnd, 2) == target_hwnd or user32.GetAncestor(fg_hwnd, 3) == target_hwnd:
            return True
        # Compare Process ID: handles multi-window games, sub-viewports, launcher-wrapped windows
        target_pid = wintypes.DWORD()
        fg_pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(target_hwnd, ctypes.byref(target_pid))
        user32.GetWindowThreadProcessId(fg_hwnd, ctypes.byref(fg_pid))
        if target_pid.value and target_pid.value == fg_pid.value:
            return True
    except Exception:
        pass
    return False

user32.IsIconic.restype = wintypes.BOOL
user32.IsIconic.argtypes = [wintypes.HWND]

def activate_window(hwnd):
    """Brings window to front without disturbing active Direct3D rendering."""
    if not is_window_alive(hwnd):
        return False
    try:
        # Only restore if actually minimized (iconic) to avoid Direct3D crashes
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        if user32.GetForegroundWindow() != hwnd:
            user32.SetForegroundWindow(hwnd)
    except Exception:
        pass
    return True
