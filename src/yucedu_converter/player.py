"""PotPlayer、VLC 与 Windows 默认播放器适配。"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .settings import AppSettings, portable_root


def player_candidates() -> list[tuple[str, Path]]:
    paths: list[tuple[str, Path]] = []
    known = [
        ("PotPlayer", Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "DAUM" / "PotPlayer" / "PotPlayerMini64.exe"),
        ("PotPlayer", Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "DAUM" / "PotPlayer" / "PotPlayerMini.exe"),
        ("VLC", Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "VideoLAN" / "VLC" / "vlc.exe"),
        ("VLC", Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "VideoLAN" / "VLC" / "vlc.exe"),
    ]
    seen: set[str] = set()
    for name, path in known:
        normalized = os.path.normcase(str(path))
        if normalized not in seen:
            seen.add(normalized)
            paths.append((name, path))
    return paths


def detected_players() -> list[tuple[str, Path]]:
    return [(name, path) for name, path in player_candidates() if path.is_file()]


def choose_player(settings: AppSettings) -> Path | None:
    custom = Path(settings.player_path) if settings.player_path else None
    if settings.player_mode == "custom":
        return custom if custom and custom.is_file() else None
    if settings.player_mode == "windows":
        return None
    available = detected_players()
    if settings.player_mode in {"potplayer", "vlc"}:
        wanted = "PotPlayer" if settings.player_mode == "potplayer" else "VLC"
        for name, path in available:
            if name == wanted:
                return path
        return None
    if custom and custom.is_file():
        return custom
    return available[0][1] if available else None


def original_player_candidates() -> list[Path]:
    root = portable_root()
    candidates = [root / "WinNetPlayer1018.exe", root.parent / "WinNetPlayer1018.exe"]
    candidates.extend(parent / "WinNetPlayer1018.exe" for parent in root.parents[:4])
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = os.path.normcase(str(candidate))
        if normalized not in seen:
            seen.add(normalized)
            unique.append(candidate)
    return unique


def choose_original_player(settings: AppSettings) -> Path | None:
    if settings.original_player_path:
        configured = Path(settings.original_player_path)
        if configured.is_file():
            return configured
    for candidate in original_player_candidates():
        if candidate.is_file():
            return candidate
    return None


def play_media(media_path: Path, settings: AppSettings) -> str:
    media_path = media_path.resolve()
    if not media_path.is_file():
        raise FileNotFoundError(f"视频文件不存在：{media_path}")
    player = choose_player(settings)
    if player is not None:
        subprocess.Popen(
            [str(player), str(media_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return str(player)
    os.startfile(media_path)
    return "Windows 默认播放器"


def play_protected_media(media_path: Path, settings: AppSettings) -> str:
    media_path = media_path.resolve()
    if not media_path.is_file():
        raise FileNotFoundError(f"YUCEdu 文件不存在：{media_path}")
    player = choose_original_player(settings)
    if player is None:
        raise FileNotFoundError("没有找到 WinNetPlayer1018.exe，请在设置中选择原播放器路径")
    subprocess.Popen(
        [str(player), str(media_path)],
        cwd=str(player.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return str(player)


def open_folder(folder: Path) -> None:
    folder = folder.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    os.startfile(folder)


def reveal_file(path: Path) -> None:
    path = path.resolve()
    if path.exists():
        subprocess.Popen(["explorer", f"/select,{path}"])
    else:
        open_folder(path.parent)
