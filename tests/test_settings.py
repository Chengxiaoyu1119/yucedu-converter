from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from yucedu_converter.settings import AppSettings, load_settings, save_settings


class SettingsTests(unittest.TestCase):
    def test_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "设置.json"
            expected = AppSettings(
                output_dir=str(Path(temp) / "输出视频"),
                encrypt_output_dir=str(Path(temp) / "加密视频"),
                player_mode="custom",
                player_path=str(Path("测试播放器") / "player.exe"),
                original_player_path=str(Path("测试播放器") / "WinNetPlayer1018.exe"),
                existing_policy="replace",
                auto_play=False,
                auto_open_folder=True,
            )
            save_settings(expected, path)
            self.assertEqual(load_settings(path), expected)

    def test_broken_json_uses_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "设置.json"
            path.write_text("{broken", encoding="utf-8")
            loaded = load_settings(path)
            self.assertTrue(loaded.output_dir)
            self.assertEqual(loaded.player_mode, "auto")

    def test_unknown_enum_values_use_safe_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "设置.json"
            path.write_text(
                '{"output_dir": ".", "player_mode": "other", "existing_policy": "unknown"}',
                encoding="utf-8",
            )
            loaded = load_settings(path)
            self.assertEqual(loaded.player_mode, "auto")
            self.assertEqual(loaded.existing_policy, "rename")


if __name__ == "__main__":
    unittest.main()
