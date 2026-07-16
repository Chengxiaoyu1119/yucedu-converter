#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "该脚本需要在 macOS 上运行。" >&2
  exit 1
fi

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST_ROOT="$PROJECT_ROOT/dist"
WORK_ROOT="$PROJECT_ROOT/build/macos"
SPEC_PATH="$PROJECT_ROOT/packaging/macos/yucedu-converter.spec"
APP_PATH="$DIST_ROOT/YUCEdu双向转换器.app"
export PYTHONPATH="$PROJECT_ROOT/src"
export MACOSX_DEPLOYMENT_TARGET="${MACOSX_DEPLOYMENT_TARGET:-12.0}"

case "$(uname -m)" in
  arm64) export YUCEDU_TARGET_ARCH="arm64" ;;
  x86_64) export YUCEDU_TARGET_ARCH="x86_64" ;;
  *) echo "未知 macOS 架构：$(uname -m)" >&2; exit 1 ;;
esac

VERSION="$(python -X utf8 "$PROJECT_ROOT/scripts/version_tool.py")"
echo "项目目录：$PROJECT_ROOT"
echo "项目版本：$VERSION"
echo "目标架构：$YUCEDU_TARGET_ARCH"

python -X utf8 "$PROJECT_ROOT/scripts/check_privacy.py"
python -X utf8 -m unittest discover -s "$PROJECT_ROOT/tests" -v
python -X utf8 -c 'import tkinter; root = tkinter.Tk(); root.withdraw(); root.destroy()'

case "$WORK_ROOT" in
  "$PROJECT_ROOT"/build/macos) rm -rf "$WORK_ROOT" ;;
  *) echo "构建路径越界：$WORK_ROOT" >&2; exit 1 ;;
esac
case "$APP_PATH" in
  "$PROJECT_ROOT"/dist/*.app) rm -rf "$APP_PATH" ;;
  *) echo "应用路径越界：$APP_PATH" >&2; exit 1 ;;
esac

python -m PyInstaller --clean --noconfirm \
  --distpath "$DIST_ROOT" \
  --workpath "$WORK_ROOT" \
  "$SPEC_PATH"

[[ -d "$APP_PATH" ]] || { echo "没有生成应用：$APP_PATH" >&2; exit 1; }
BINARY="$APP_PATH/Contents/MacOS/YUCEduConverter"
[[ -x "$BINARY" ]] || { echo "应用主程序缺失：$BINARY" >&2; exit 1; }

ACTUAL_VERSION="$("$BINARY" --version)"
[[ "$ACTUAL_VERSION" == "$VERSION" ]] || {
  echo "应用版本不一致：项目=$VERSION，应用=$ACTUAL_VERSION" >&2
  exit 1
}
"$BINARY" --smoke-test
plutil -lint "$APP_PATH/Contents/Info.plist"
codesign --verify --deep --strict --verbose=2 "$APP_PATH"
file "$BINARY"

echo "macOS 构建成功：$APP_PATH"
