from __future__ import annotations

import ctypes
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path


def main() -> int:
    exe = Path(sys.argv[1]).resolve()
    process = subprocess.Popen([str(exe)])
    user32 = ctypes.windll.user32
    windows: list[int] = []
    enum_type = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    @enum_type
    def enum_window(hwnd: int, _lparam: int) -> bool:
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == process.pid and user32.IsWindowVisible(hwnd):
            windows.append(hwnd)
        return True

    try:
        deadline = time.time() + 15
        while time.time() < deadline and not windows and process.poll() is None:
            windows.clear()
            user32.EnumWindows(enum_window, 0)
            time.sleep(0.2)
        if not windows:
            raise RuntimeError("启动后没有找到主窗口")
        get_class = getattr(user32, "GetClassLongPtrW", user32.GetClassLongW)
        get_class.restype = ctypes.c_void_p
        handles = [get_class(windows[0], -14), get_class(windows[0], -34)]
        if not any(handles):
            raise RuntimeError("窗口类没有图标句柄")
        print(f"WINDOW_ICON_OK|{handles[0]}|{handles[1]}")
        return 0
    finally:
        if windows:
            user32.PostMessageW(windows[0], 0x0010, 0, 0)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
