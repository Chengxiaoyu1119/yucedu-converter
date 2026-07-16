# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(SPECPATH).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
PACKAGE_ROOT = SOURCE_ROOT / "yucedu_converter"
RESOURCE_ROOT = PACKAGE_ROOT / "resources"
sys.path.insert(0, str(SOURCE_ROOT))

from yucedu_converter import APP_VERSION

TARGET_ARCH = os.environ.get("YUCEDU_TARGET_ARCH") or None


a = Analysis(
    [str(PROJECT_ROOT / "packaging" / "macos" / "launcher.py")],
    pathex=[str(SOURCE_ROOT)],
    binaries=[],
    datas=[
        (str(RESOURCE_ROOT / "aes_tail_table.bin"), "yucedu_converter/resources"),
        (str(RESOURCE_ROOT / "compatibility_trailer.bin"), "yucedu_converter/resources"),
        (str(RESOURCE_ROOT / "app.ico"), "yucedu_converter/resources"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["numpy", "pytest"],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="YUCEduConverter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=TARGET_ARCH,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="YUCEduConverter",
)

app = BUNDLE(
    coll,
    name="YUCEdu双向转换器.app",
    icon=str(RESOURCE_ROOT / "app.ico"),
    bundle_identifier="io.github.chengxiaoyu1119.yucedu-converter",
    version=APP_VERSION,
    info_plist={
        "CFBundleDisplayName": "YUCEdu 双向转换器",
        "CFBundleName": "YUCEdu 双向转换器",
        "CFBundleShortVersionString": APP_VERSION,
        "CFBundleVersion": APP_VERSION,
        "LSApplicationCategoryType": "public.app-category.utilities",
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
    },
)
