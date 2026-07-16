from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from yucedu_converter import APP_VERSION  # noqa: E402


def version_tuple(version: str) -> tuple[int, int, int, int]:
    parts = version.split(".")
    if not 1 <= len(parts) <= 4 or any(not part.isdecimal() for part in parts):
        raise ValueError(f"版本号必须由数字和点组成：{version}")
    values = [int(part) for part in parts]
    values.extend([0] * (4 - len(values)))
    return tuple(values[:4])


def write_windows_info(output: Path) -> None:
    template_path = PROJECT_ROOT / "packaging" / "windows" / "version_info.template.txt"
    template = template_path.read_text(encoding="utf-8")
    tuple_text = ", ".join(str(value) for value in version_tuple(APP_VERSION))
    rendered = template.replace("@VERSION_TUPLE@", tuple_text).replace("@VERSION@", APP_VERSION)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="读取并验证 yucedu-converter 单一版本号")
    parser.add_argument("--check-tag", metavar="TAG")
    parser.add_argument("--write-windows-info", type=Path, metavar="PATH")
    args = parser.parse_args()

    if args.check_tag and args.check_tag != f"v{APP_VERSION}":
        parser.error(f"标签 {args.check_tag} 与项目版本 v{APP_VERSION} 不一致")
    if args.write_windows_info:
        write_windows_info(args.write_windows_info.resolve())
    print(APP_VERSION)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
