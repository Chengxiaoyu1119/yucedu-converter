"""Windows、macOS 与 Linux 的播放器和文件管理器适配。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .settings import AppSettings, portable_root


def _is_launchable(path: Path) -> bool:
    if path.is_file():
        return True
    return sys.platform == "darwin" and path.suffix.lower() == ".app" and path.is_dir()


def _unique_candidates(items: list[tuple[str, Path]]) -> list[tuple[str, Path]]:
    unique: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for name, path in items:
        normalized = os.path.normcase(str(path))
        if normalized not in seen:
            seen.add(normalized)
            unique.append((name, path))
    return unique


def player_candidates() -> list[tuple[str, Path]]:
    if sys.platform == "darwin":
        applications = Path("/Applications")
        user_applications = Path.home() / "Applications"
        return _unique_candidates(
            [
                ("IINA", applications / "IINA.app"),
                ("IINA", user_applications / "IINA.app"),
                ("VLC", applications / "VLC.app"),
                ("VLC", user_applications / "VLC.app"),
            ]
        )
    if sys.platform == "win32":
        return _unique_candidates(
            [
                (
                    "PotPlayer",
                    Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
                    / "DAUM"
                    / "PotPlayer"
                    / "PotPlayerMini64.exe",
                ),
                (
                    "PotPlayer",
                    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
                    / "DAUM"
                    / "PotPlayer"
                    / "PotPlayerMini.exe",
                ),
                (
                    "VLC",
                    Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
                    / "VideoLAN"
                    / "VLC"
                    / "vlc.exe",
                ),
                (
                    "VLC",
                    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
                    / "VideoLAN"
                    / "VLC"
                    / "vlc.exe",
                ),
            ]
        )
    return [("VLC", Path("/usr/bin/vlc"))]


def detected_players() -> list[tuple[str, Path]]:
    return [(name, path) for name, path in player_candidates() if _is_launchable(path)]


def choose_player(settings: AppSettings) -> Path | None:
    custom = Path(settings.player_path).expanduser() if settings.player_path else None
    if settings.player_mode == "custom":
        return custom if custom and _is_launchable(custom) else None
    if settings.player_mode in {"windows", "system"}:
        return None

    available = detected_players()
    wanted_names = {"potplayer": "PotPlayer", "iina": "IINA", "vlc": "VLC"}
    wanted = wanted_names.get(settings.player_mode)
    if wanted:
        for name, path in available:
            if name == wanted:
                return path
        return None
    if custom and _is_launchable(custom):
        return custom
    return available[0][1] if available else None


def original_player_candidates() -> list[Path]:
    root = portable_root()
    if sys.platform == "darwin":
        candidates = [
            root / "MacNetPlayer.app",
            root.parent / "MacNetPlayer.app",
            Path("/Applications/MacNetPlayer.app"),
            Path.home() / "Applications" / "MacNetPlayer.app",
        ]
        candidates.extend(parent / "MacNetPlayer.app" for parent in root.parents[:4])
    elif sys.platform == "win32":
        candidates = [root / "WinNetPlayer1018.exe", root.parent / "WinNetPlayer1018.exe"]
        candidates.extend(parent / "WinNetPlayer1018.exe" for parent in root.parents[:4])
    else:
        candidates = []

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
        configured = Path(settings.original_player_path).expanduser()
        if _is_launchable(configured):
            return configured
    for candidate in original_player_candidates():
        if _is_launchable(candidate):
            return candidate
    return None


def _spawn(command: list[str], *, cwd: Path | None = None) -> None:
    subprocess.Popen(
        command,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _open_with_default(path: Path) -> str:
    if sys.platform == "win32":
        os.startfile(path)
        return "Windows 默认应用"
    if sys.platform == "darwin":
        _spawn(["open", str(path)])
        return "macOS 默认应用"
    _spawn(["xdg-open", str(path)])
    return "系统默认应用"


def _open_with_player(player: Path, media_path: Path) -> None:
    if sys.platform == "darwin" and player.suffix.lower() == ".app":
        _spawn(["open", "-a", str(player), str(media_path)])
        return
    _spawn([str(player), str(media_path)], cwd=player.parent)


def play_media(media_path: Path, settings: AppSettings) -> str:
    media_path = media_path.resolve()
    if not media_path.is_file():
        raise FileNotFoundError(f"视频文件不存在：{media_path}")
    player = choose_player(settings)
    if player is not None:
        _open_with_player(player, media_path)
        return str(player)
    return _open_with_default(media_path)


def play_protected_media(media_path: Path, settings: AppSettings) -> str:
    media_path = media_path.resolve()
    if not media_path.is_file():
        raise FileNotFoundError(f"YUCEdu 文件不存在：{media_path}")
    player = choose_original_player(settings)
    if player is None:
        expected = "MacNetPlayer.app" if sys.platform == "darwin" else "WinNetPlayer1018.exe"
        raise FileNotFoundError(f"没有找到 {expected}，请在设置中选择原播放器路径")
    _open_with_player(player, media_path)
    return str(player)


def open_folder(folder: Path) -> None:
    folder = folder.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    _open_with_default(folder)


def reveal_file(path: Path) -> None:
    path = path.resolve()
    if not path.exists():
        open_folder(path.parent)
        return
    if sys.platform == "win32":
        _spawn(["explorer", f"/select,{path}"])
    elif sys.platform == "darwin":
        _spawn(["open", "-R", str(path)])
    else:
        open_folder(path.parent)
