# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


PROJECT_ROOT = Path(SPECPATH).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
PACKAGE_ROOT = SOURCE_ROOT / "yucedu_converter"
RESOURCE_ROOT = PACKAGE_ROOT / "resources"

a = Analysis(
    [str(PROJECT_ROOT / "packaging" / "windows" / "launcher.py")],
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
    excludes=["PIL", "numpy", "pytest"],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="YUCEdu双向转换器",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    contents_directory="运行组件",
    codesign_identity=None,
    entitlements_file=None,
    icon=str(RESOURCE_ROOT / "app.ico"),
    version=str(PROJECT_ROOT / "packaging" / "windows" / "version_info.txt"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="YUCEdu双向转换器",
)
