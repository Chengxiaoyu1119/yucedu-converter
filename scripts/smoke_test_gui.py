from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path


def main() -> int:
    exe = Path(sys.argv[1]).resolve()
    if not exe.is_file():
        raise FileNotFoundError(exe)

    windows_dir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    environment = os.environ.copy()
    environment["PATH"] = os.pathsep.join([str(windows_dir / "System32"), str(windows_dir)])
    process = subprocess.Popen([str(exe)], env=environment)

    user32 = ctypes.windll.user32
    windows: list[tuple[int, str]] = []
    enum_type = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    @enum_type
    def enum_window(hwnd: int, _lparam: int) -> bool:
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == process.pid and user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            title = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, title, length + 1)
            if title.value:
                windows.append((hwnd, title.value))
        return True

    try:
        deadline = time.time() + 15
        while time.time() < deadline and not windows and process.poll() is None:
            windows.clear()
            user32.EnumWindows(enum_window, 0)
            if not windows:
                time.sleep(0.2)
        if process.poll() is not None:
            raise RuntimeError(f"程序提前退出：{process.returncode}")
        if not windows:
            raise RuntimeError("启动后没有找到主窗口")
        title = windows[0][1]
        if title != "YUCEdu 双向转换器":
            raise RuntimeError(f"主窗口标题异常：{title}")
        print(f"PACKAGED_GUI_OK|{title}|PID={process.pid}")
        return 0
    finally:
        if windows:
            user32.PostMessageW(windows[0][0], 0x0010, 0, 0)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
