"""YUCEdu 离线转换器正式版入口。"""

from __future__ import annotations

import ctypes
import sys


def enable_windows_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "YUCEdu.BidirectionalConverter.2.0.1"
        )
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main() -> int:
    enable_windows_dpi_awareness()
    from .gui import run_app

    run_app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
