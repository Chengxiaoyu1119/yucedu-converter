"""用户设置、程序资源和日志目录。"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class AppSettings:
    output_dir: str
    encrypt_output_dir: str = ""
    player_mode: str = "auto"
    player_path: str = ""
    original_player_path: str = ""
    existing_policy: str = "rename"
    auto_play: bool = True
    auto_open_folder: bool = False


def portable_root() -> Path:
    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).resolve()
        if sys.platform == "darwin":
            for parent in executable.parents:
                if parent.suffix.lower() == ".app":
                    return parent.parent
        return executable.parent
    return Path(__file__).resolve().parents[1]


def resource_path(filename: str) -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root) / "yucedu_converter" / "resources" / filename
    return Path(__file__).resolve().with_name("resources") / filename


def app_data_dir() -> Path:
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA")
        base = Path(local) if local else Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        config_home = os.environ.get("XDG_CONFIG_HOME")
        base = Path(config_home) if config_home else Path.home() / ".config"
    return base / "YUCEdu双向转换器"


def settings_path() -> Path:
    return app_data_dir() / "设置.json"


def log_path() -> Path:
    log_dir = app_data_dir() / "日志"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"转换器-{datetime.now():%Y%m%d}.log"


def default_settings() -> AppSettings:
    if sys.platform == "darwin":
        base = Path.home() / "Movies" / "YUCEdu双向转换器"
    else:
        base = portable_root()
    return AppSettings(
        output_dir=str(base / "输出视频"),
        encrypt_output_dir=str(base / "加密视频"),
    )


def load_settings(path: Path | None = None) -> AppSettings:
    target = path or settings_path()
    defaults = default_settings()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError, TypeError):
        return defaults
    if not isinstance(raw, dict):
        return defaults
    player_mode = str(raw.get("player_mode") or "auto")
    if player_mode not in {"auto", "potplayer", "iina", "vlc", "windows", "system", "custom"}:
        player_mode = "auto"
    existing_policy = str(raw.get("existing_policy") or "rename")
    if existing_policy not in {"rename", "error", "replace"}:
        existing_policy = "rename"
    return AppSettings(
        output_dir=str(raw.get("output_dir") or defaults.output_dir),
        encrypt_output_dir=str(raw.get("encrypt_output_dir") or defaults.encrypt_output_dir),
        player_mode=player_mode,
        player_path=str(raw.get("player_path") or ""),
        original_player_path=str(raw.get("original_player_path") or ""),
        existing_policy=existing_policy,
        auto_play=bool(raw.get("auto_play", True)),
        auto_open_folder=bool(raw.get("auto_open_folder", False)),
    )


def save_settings(settings: AppSettings, path: Path | None = None) -> None:
    target = path or settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(
        json.dumps(asdict(settings), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary, target)
