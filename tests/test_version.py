from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

from yucedu_converter import APP_VERSION
from yucedu_converter.main import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "version_tool",
    PROJECT_ROOT / "scripts" / "version_tool.py",
)
assert SPEC and SPEC.loader
VERSION_TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERSION_TOOL)


class VersionTests(unittest.TestCase):
    def test_cli_version_uses_package_version(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main(["--version"])
        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue().strip(), APP_VERSION)

    def test_version_tuple_is_windows_compatible(self) -> None:
        self.assertEqual(VERSION_TOOL.version_tuple(APP_VERSION), (2, 1, 0, 0))

    def test_windows_version_info_is_generated_from_single_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "version_info.txt"
            VERSION_TOOL.write_windows_info(output)
            rendered = output.read_text(encoding="utf-8")
        self.assertIn(f"FileVersion', '{APP_VERSION}'", rendered)
        self.assertIn("filevers=(2, 1, 0, 0)", rendered)
        self.assertNotIn("@VERSION@", rendered)


if __name__ == "__main__":
    unittest.main()
