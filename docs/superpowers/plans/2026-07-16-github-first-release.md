# yucedu-converter First Public Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Publish the tested Windows 2.0.1 converter as the public GitHub repository `yucedu-converter` with CI, source documentation, tag `v2.0.1`, and verified release assets.

**Architecture:** Keep the verified Python conversion engine and Tkinter desktop GUI, move them into a standard `src/yucedu_converter` package, and keep PyInstaller packaging under `packaging/windows`. Store original players and real media outside Git while documenting their provenance and hashes.

**Tech Stack:** Python 3.13, Tkinter/ttk, cryptography 44.0.1, PyInstaller 6.21.0, unittest, PowerShell, GitHub Actions, GitHub CLI.

## Global Constraints

- Repository root is the checked-out `<project-root>` directory.
- Repository name is exactly `yucedu-converter`.
- Public license is MIT.
- Initial version and tag are `2.0.1` and `v2.0.1`.
- Do not commit `WinNetPlayer1018.exe`, `MacNetPlayer.app`, real `.yucedu` files, decrypted media, build caches, logs, or release archives.
- Preserve byte-for-byte behavior of the verified conversion engine and compatibility resources.
- Run all available tests before commit and again before release.

---

### Task 1: Create the standard source tree

**Files:**
- Create: `src/yucedu_converter/__init__.py`
- Create: `src/yucedu_converter/__main__.py`
- Create: `src/yucedu_converter/converter.py`
- Create: `src/yucedu_converter/gui.py`
- Create: `src/yucedu_converter/main.py`
- Create: `src/yucedu_converter/player.py`
- Create: `src/yucedu_converter/settings.py`
- Create: `src/yucedu_converter/theme.py`
- Create: `src/yucedu_converter/resources/aes_tail_table.bin`
- Create: `src/yucedu_converter/resources/compatibility_trailer.bin`
- Create: `src/yucedu_converter/resources/app.ico`

**Interfaces:**
- Consumes: verified source under `逆向案例/winnetplayer1018/双向版源码/app`.
- Produces: importable package `yucedu_converter` and entry point `yucedu_converter.__main__:main`.

- [x] Copy the verified modules into `src/yucedu_converter`.
- [x] Rename `converter_core.py` to `converter.py` and update all relative imports from `.converter_core` to `.converter`.
- [x] Replace resource filenames in `settings.resource_path()` callers with `aes_tail_table.bin`, `compatibility_trailer.bin`, and `app.ico`.
- [x] Copy binary resources and verify these fixed hashes:

```text
aes_tail_table.bin           6a7b62339ea7bc0e0e42b9f8f52b6f83a9a7e6db1fb410c26e9450be1443cb98
compatibility_trailer.bin    0e62fcd7e24af3f55872cf3904d1665301ce8fa41a524aa0bb96183de4b53974
app.ico                      ca733443f59225c957d44d038923edaf2c4a1a82f70b53dcb75ef60844f0154a
```

- [x] Create `__main__.py` with:

```python
from .main import main

if __name__ == "__main__":
    raise SystemExit(main())
```

- [x] Verify package compilation:

```powershell
$env:PYTHONPATH = "$PWD\src"
python -X utf8 -m compileall -q src
```

Expected: exit code 0.

### Task 2: Migrate and normalize tests

**Files:**
- Create: `tests/test_converter.py`
- Create: `tests/test_regression_fixture.py`
- Create: `tests/test_player.py`
- Create: `tests/test_settings.py`
- Create: `tests/fixtures/README.md`

**Interfaces:**
- Consumes: `yucedu_converter.converter`, `yucedu_converter.player`, and `yucedu_converter.settings`.
- Produces: unittest discovery suite runnable without private media.

- [x] Copy the four existing test modules and update imports from `app` to `yucedu_converter`.
- [x] Update resource paths to `src/yucedu_converter/resources`.
- [x] Change the real-sample path in `test_regression_fixture.py` to:

```python
import os

SAMPLE_VALUE = os.environ.get("YUCEDU_REGRESSION_SAMPLE", "")
SAMPLE = Path(SAMPLE_VALUE) if SAMPLE_VALUE else Path("__fixture_not_configured__")
```

- [x] Preserve `@unittest.skipUnless(SAMPLE.is_file(), ...)` so public CI skips only the private fixture test.
- [x] Add `tests/fixtures/README.md` explaining that public fixtures must be synthetic and contain no original player or real course media.
- [x] Run:

```powershell
$env:PYTHONPATH = "$PWD\src"
$env:YUCEDU_REGRESSION_SAMPLE = "<私有样本目录>/regression.yucedu"
python -X utf8 -m unittest discover -s tests -v
```

Expected: 20 tests pass.

### Task 3: Add project metadata and user documentation

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `LICENSE`
- Create: `CHANGELOG.md`
- Create: `CONTRIBUTING.md`
- Create: `SECURITY.md`
- Create: `THIRD_PARTY_NOTICES.md`
- Create: `.gitignore`
- Create: `.gitattributes`
- Create: `.editorconfig`
- Create: `docs/使用说明.md`
- Create: `docs/测试与兼容报告.md`
- Create: `docs/多平台路线图.md`
- Create: `docs/research/上游播放器来源.md`
- Create: `docs/research/MacNetPlayer本地分析.md`
- Create: `docs/images/Windows主界面.png`
- Create: `docs/images/现代滚动条.png`

**Interfaces:**
- Consumes: version `2.0.1`, local validation results, official player URL, and local Mac bundle audit.
- Produces: installable project metadata and complete public landing page.

- [x] Add `pyproject.toml` with setuptools src layout, Python `>=3.11`, runtime dependency `cryptography==44.0.1`, and build extras `pyinstaller==6.21.0`.
- [x] Add MIT license text with copyright year 2026.
- [x] Add ignore rules for `.exe`, `.app`, `.yucedu`, video formats, ZIP files, caches, logs, `build`, `dist`, and `release`.
- [x] Write README with screenshot, features, quick start, supported formats, build commands, source references, current limitations, and roadmap.
- [x] Record the official source page `https://www.drmsoft.cn/playernetN7.2/down.asp` and both official player download filenames.
- [x] Record the inspected Mac main binary hash `5b8d395dd7086fffA87ca68f1d7252303b85bc9badd479748ac86c5b65a3ef52`, x86_64 architecture, Bundle version 1.0.0, and bundled FFmpeg/SDL2 libraries.
- [x] Copy the verified 2.0.1 GUI screenshots into `docs/images`.

### Task 4: Add Windows packaging and GitHub automation

**Files:**
- Create: `packaging/windows/yucedu-converter.spec`
- Create: `packaging/windows/version_info.txt`
- Create: `scripts/build_windows.ps1`
- Create: `scripts/package_release.ps1`
- Create: `.github/workflows/test-windows.yml`
- Create: `.github/workflows/release-windows.yml`
- Create: `.github/ISSUE_TEMPLATE/bug.yml`
- Create: `.github/ISSUE_TEMPLATE/feature.yml`
- Create: `.github/pull_request_template.md`

**Interfaces:**
- Consumes: `src/yucedu_converter` and project metadata.
- Produces: reproducible Windows onedir build, ZIP, SHA256, CI checks, and tag artifacts.

- [x] Adapt the current PyInstaller spec to `src/yucedu_converter` and English resource filenames.
- [x] Preserve the app name `YUCEdu双向转换器`, version 2.0.1, icon, and windowed mode.
- [x] Make `scripts/build_windows.ps1` run tests before PyInstaller.
- [x] Make `scripts/package_release.ps1` create the single `release/yucedu-converter-v2.0.1-windows-x64.zip` asset and its `.sha256.txt` file.
- [x] Configure `test-windows.yml` for push and pull request on Python 3.13.
- [x] Configure `release-windows.yml` for tags matching `v*`, build the app, package it, and upload both release files as Actions artifacts.
- [x] Validate workflow YAML with Python `yaml.safe_load` when PyYAML is available and manually inspect all paths.

### Task 5: Validate the repository and release artifacts

**Files:**
- Generate locally: `dist/YUCEdu双向转换器/`
- Generate locally: `release/yucedu-converter-v2.0.1-windows-x64/`
- Generate locally: `release/yucedu-converter-v2.0.1-windows-x64.zip`
- Generate locally: `release/yucedu-converter-v2.0.1-windows-x64.zip.sha256.txt`

**Interfaces:**
- Consumes: source tree, tests, packaging scripts, and private regression fixture path.
- Produces: release-ready verified assets.

- [x] Run all tests with the private fixture configured and confirm 20 passes.
- [x] Run `scripts/build_windows.ps1` and confirm the EXE starts with a minimal Windows PATH.
- [x] Confirm the startup output location is empty and both scrollbars are hidden for an empty task table.
- [x] Confirm the window icon handle is present.
- [x] Run `scripts/package_release.ps1`.
- [x] Open the ZIP, compare every archived file hash against the release directory, and confirm zero missing, extra, or mismatched files.
- [x] Scan tracked candidates and confirm no `.exe`, `.app`, `.yucedu`, ordinary video, log, cache, or ZIP is staged.

### Task 6: Initialize Git and publish GitHub release

**Files:**
- Create: `.git/`
- Publish: GitHub repository `yucedu-converter`
- Publish: tag and Release `v2.0.1`

**Interfaces:**
- Consumes: clean validated repository and local verified release assets.
- Produces: public `main`, passing Actions, tag `v2.0.1`, and downloadable release files.

- [x] Initialize and commit:

```powershell
git init -b main
git add .
git status --short
git commit -m "release: publish yucedu-converter v2.0.1"
```

- [x] Authenticate GitHub CLI with browser login:

```powershell
gh auth login --hostname github.com --git-protocol https --web
gh auth status
```

- [x] Create and push the public repository:

```powershell
gh repo create yucedu-converter --public --source . --remote origin --push --description "YUCEdu bidirectional converter with batch encrypt, decrypt, validation, and Windows GUI"
```

- [x] Tag and push:

```powershell
git tag -a v2.0.1 -m "YUCEdu Converter 2.0.1"
git push origin v2.0.1
```

- [x] Create the GitHub Release:

```powershell
gh release create v2.0.1 `
  "release/yucedu-converter-v2.0.1-windows-x64.zip" `
  "release/yucedu-converter-v2.0.1-windows-x64.zip.sha256.txt" `
  --title "YUCEdu 双向转换器 2.0.1" `
  --notes-file "CHANGELOG.md"
```

- [x] Verify online state:

```powershell
gh repo view --web
gh run list --limit 10
gh release view v2.0.1
git status --short
```

Expected: repository is public, `main` is pushed, workflows are visible, release has two assets, and the local working tree is clean.
