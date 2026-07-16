from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yucedu_converter.player import choose_original_player, choose_player, play_media
from yucedu_converter.settings import AppSettings


class PlayerTests(unittest.TestCase):
    def test_windows_mode_uses_default_player(self) -> None:
        settings = AppSettings(output_dir=".", player_mode="windows")
        self.assertIsNone(choose_player(settings))

    @patch("yucedu_converter.player.detected_players", return_value=[])
    def test_auto_without_player_falls_back(self, _mocked) -> None:
        settings = AppSettings(output_dir=".", player_mode="auto")
        self.assertIsNone(choose_player(settings))

    def test_configured_original_player_is_used(self) -> None:
        with patch("pathlib.Path.is_file", return_value=True):
            settings = AppSettings(
                output_dir=".",
                original_player_path=str(Path("测试播放器") / "WinNetPlayer1018.exe"),
            )
            self.assertEqual(
                str(choose_original_player(settings)),
                str(Path("测试播放器") / "WinNetPlayer1018.exe"),
            )

    def test_macos_app_bundle_is_launchable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            app = Path(temp) / "MacNetPlayer.app"
            app.mkdir()
            settings = AppSettings(output_dir=".", original_player_path=str(app))
            with patch("yucedu_converter.player.sys.platform", "darwin"):
                self.assertEqual(choose_original_player(settings), app)

    def test_macos_default_player_uses_open(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            media = Path(temp) / "video.mp4"
            media.write_bytes(b"fixture")
            settings = AppSettings(output_dir=".", player_mode="system")
            with (
                patch("yucedu_converter.player.sys.platform", "darwin"),
                patch("yucedu_converter.player.subprocess.Popen") as popen,
            ):
                result = play_media(media, settings)
            self.assertEqual(result, "macOS 默认应用")
            self.assertEqual(popen.call_args.args[0], ["open", str(media.resolve())])


if __name__ == "__main__":
    unittest.main()
