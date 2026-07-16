# yucedu-converter

[![Cross-platform CI](https://img.shields.io/badge/Windows%20%2B%20macOS-CI-2671E5)](.github/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-2.1.0-2671E5)](docs/更新日志.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

YUCEdu 双向转换器：提供 Windows 与 macOS 图形界面、批量任务、文件校验，以及当前已验证配置下的 `.yucedu` 解密与反向加密。

当前稳定版本：`2.1.0`

![Windows 主界面](docs/images/Windows主界面.png)

## 功能

- 解密 `.yucedu` 为普通视频。
- 把 MP4、MKV、AVI、MOV、M4V、WMV、FLV、WebM、TS、MPEG、MPG 加密为 `.yucedu`。
- 多文件和文件夹批量任务。
- 当前文件进度、总进度和速度显示。
- 取消任务、临时文件清理和自动改名。
- 每次启动后由用户选择输出文件夹。
- 解密结果调用系统默认播放器、PotPlayer、IINA 或 VLC。
- 加密结果可调用 Windows `WinNetPlayer1018.exe` 或 macOS `MacNetPlayer.app` 验证。
- Windows 标题栏、任务栏图标与 macOS App/Dock 图标。

## 下载

从 [Releases](https://github.com/Chengxiaoyu1119/yucedu-converter/releases) 选择设备对应文件：

| 平台 | 下载文件 |
|---|---|
| Windows 10/11 x64 | `yucedu-converter-v2.1.0-windows-x64.zip` |
| Apple Silicon（M1/M2/M3/M4 等） | `yucedu-converter-v2.1.0-macos-arm64.dmg` |
| Intel Mac | `yucedu-converter-v2.1.0-macos-x64.dmg` |

每个安装包都配有 `.sha256.txt` 校验文件。

## 快速使用

### Windows

1. 完整解压 Windows ZIP。
2. 双击 `YUCEdu双向转换器.exe`。
3. 选择“解密”或“加密”。
4. 点击“选择文件夹”决定输出位置。
5. 添加文件并开始处理。

### macOS

1. 打开与 Mac 芯片匹配的 DMG。
2. 把 `YUCEdu双向转换器.app` 拖入 `Applications`。
3. 首次启动时按住 Control 点击应用，再选择“打开”。
4. 选择模式、输出位置和文件，然后开始处理。

macOS 的安装、播放器和 Gatekeeper 说明见 [macOS 使用说明](docs/macOS说明.md)。

```text
选择模式 → 选择输出文件夹 → 添加文件 → 开始处理
```

## 从源码运行

要求：Python 3.11 或更高版本。

Windows：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m yucedu_converter
```

macOS：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m yucedu_converter
```

## 测试

公开测试套件只使用合成数据：

```powershell
$env:PYTHONPATH = "$PWD\src"
python -X utf8 -m unittest discover -s tests -v
```

## 构建

Windows：

```powershell
python -m pip install -e ".[build]"
.\scriptsuild_windows.ps1
.\scripts\package_release.ps1
```

macOS：

```bash
python -m pip install -e ".[macos]"
bash scripts/build_macos.sh
bash scripts/package_macos.sh
```

详细步骤见 [构建说明](docs/构建说明.md)。标签 `v*` 会通过 GitHub Actions 自动构建 Windows、macOS arm64 和 macOS x64，并创建 Release。

## 当前兼容范围

| 项目 | 状态 |
|---|---|
| Windows 10/11 x64 | 已验证 |
| macOS 15 Apple Silicon | 自动构建与启动检查通过后发布 |
| macOS 15 Intel | 自动构建与启动检查通过后发布 |
| 解密 `.yucedu` | 当前已验证配置支持 |
| 普通视频反向加密 | 当前已验证配置支持 |
| WinNetPlayer1018 调用 | Windows 支持 |
| MacNetPlayer 调用 | macOS 支持 |
| Linux / Android / iOS | 路线图阶段 |

不同来源的 `.yucedu` 可能使用不同配置。项目通过资源校验和回归测试维护当前已验证配置。

## 项目文档

- [使用说明](docs/使用说明.md)
- [macOS 使用说明](docs/macOS说明.md)
- [项目结构、技术栈与路径规范](docs/项目结构.md)
- [转换格式说明](docs/格式说明.md)
- [Windows 与 macOS 构建说明](docs/构建说明.md)
- [发布包说明](docs/发布说明.md)
- [兼容报告](docs/兼容报告.md)
- [更新日志](docs/更新日志.md)
- [多平台路线图](docs/路线图.md)
- [第三方组件](docs/第三方组件.md)
- [参与贡献](.github/CONTRIBUTING.md)
- [安全说明](.github/SECURITY.md)

## 上游参考资料

- [网络播放器下载中心](https://www.drmsoft.cn/playernetN7.2/down.asp)
- [Windows 播放器下载地址](https://fuwu2.drmsoft.net/drmsoft/WinNetPlayer1018.zip)
- [macOS 播放器下载地址](https://fuwu2.drmsoft.net/player/N7.2/MacNetPlayerN7.2.zip)

原播放器、Mac 应用和真实媒体保存在仓库外；仓库只记录公开来源、结构、哈希和兼容测试结论。

## 许可证

项目源码使用 [MIT License](LICENSE)。第三方组件信息见 [第三方组件说明](docs/第三方组件.md)。
