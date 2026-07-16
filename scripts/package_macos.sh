#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "该脚本需要在 macOS 上运行。" >&2
  exit 1
fi

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_PATH="$PROJECT_ROOT/dist/YUCEdu双向转换器.app"
RELEASE_ROOT="$PROJECT_ROOT/release"
export PYTHONPATH="$PROJECT_ROOT/src"
VERSION="$(python -X utf8 "$PROJECT_ROOT/scripts/version_tool.py")"

NATIVE_ARCH="$(uname -m)"
REQUESTED_ARCH="${1:-$NATIVE_ARCH}"
case "$REQUESTED_ARCH" in
  arm64) ASSET_ARCH="arm64"; FILE_ARCH="arm64" ;;
  x64|x86_64) ASSET_ARCH="x64"; FILE_ARCH="x86_64" ;;
  *) echo "架构参数应为 arm64、x64 或 x86_64：$REQUESTED_ARCH" >&2; exit 1 ;;
esac

[[ -d "$APP_PATH" ]] || { echo "请先运行 scripts/build_macos.sh" >&2; exit 1; }
BINARY="$APP_PATH/Contents/MacOS/YUCEduConverter"
file "$BINARY" | grep -q "$FILE_ARCH" || {
  echo "应用架构与资产名称不一致：$(file "$BINARY")" >&2
  exit 1
}

ASSET_BASE="yucedu-converter-v${VERSION}-macos-${ASSET_ARCH}"
STAGE_ROOT="$RELEASE_ROOT/.stage-${ASSET_BASE}"
DMG_PATH="$RELEASE_ROOT/${ASSET_BASE}.dmg"
HASH_PATH="${DMG_PATH}.sha256.txt"
mkdir -p "$RELEASE_ROOT"

for path in "$STAGE_ROOT" "$DMG_PATH" "$HASH_PATH"; do
  case "$path" in
    "$RELEASE_ROOT"/*) ;;
    *) echo "发布路径越界：$path" >&2; exit 1 ;;
  esac
done
rm -rf "$STAGE_ROOT"
rm -f "$DMG_PATH" "$HASH_PATH"
mkdir -p "$STAGE_ROOT"

codesign --force --deep --sign - "$APP_PATH"
codesign --verify --deep --strict --verbose=2 "$APP_PATH"
ditto "$APP_PATH" "$STAGE_ROOT/YUCEdu双向转换器.app"
ln -s /Applications "$STAGE_ROOT/Applications"
cp "$PROJECT_ROOT/docs/使用说明.md" "$STAGE_ROOT/使用说明.md"

hdiutil create \
  -volname "YUCEdu 双向转换器 ${VERSION}" \
  -srcfolder "$STAGE_ROOT" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

HASH="$(shasum -a 256 "$DMG_PATH" | awk '{print $1}')"
printf '%s  %s\n' "$HASH" "$(basename "$DMG_PATH")" > "$HASH_PATH"
rm -rf "$STAGE_ROOT"

echo "macOS DMG：$DMG_PATH"
echo "SHA256：$HASH"
