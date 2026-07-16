from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from yucedu_converter.player import choose_original_player, choose_player
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


if __name__ == "__main__":
    unittest.main()
