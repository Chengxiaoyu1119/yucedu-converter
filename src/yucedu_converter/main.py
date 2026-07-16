"""YUCEdu 双向转换器入口。"""

from __future__ import annotations

import ctypes
import sys
from collections.abc import Sequence

from . import APP_VERSION


def enable_windows_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            f"YUCEdu.BidirectionalConverter.{APP_VERSION}"
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


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if "--version" in arguments:
        print(APP_VERSION)
        return 0

    enable_windows_dpi_awareness()
    from .gui import run_app

    run_app(smoke_test="--smoke-test" in arguments)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
