# yucedu-converter

[![Windows CI](https://img.shields.io/badge/Windows-CI-2671E5)](.github/workflows/test-windows.yml)
[![Version](https://img.shields.io/badge/version-2.0.1-2671E5)](docs/更新日志.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

YUCEdu 双向转换器：提供 Windows 图形界面、批量任务、文件校验，以及当前已验证配置下的 `.yucedu` 解密与反向加密。

当前稳定版本：`2.0.1`

![Windows 主界面](docs/images/Windows主界面.png)

## 功能

- 解密 `.yucedu` 为普通视频。
- 把 MP4、MKV、AVI、MOV、M4V、WMV、FLV、WebM、TS、MPEG、MPG 加密为 `.yucedu`。
- 多文件和文件夹批量任务。
- 当前文件进度、总进度和速度显示。
- 取消任务、临时文件清理和自动改名。
- 每次启动后由用户选择输出文件夹。
- 内容较少时自动隐藏滚动条，长列表显示细条式滚动条。
- 解密结果调用 PotPlayer、VLC 或 Windows 默认播放器。
- 加密结果调用本地 `WinNetPlayer1018.exe` 进行兼容验证。
- Windows 标题栏和任务栏独立图标。

## 快速使用

正式版用户：

1. 从 [Releases](https://github.com/Chengxiaoyu1119/yucedu-converter/releases) 页面获取 `yucedu-converter-v2.0.1-windows-x64.zip`。
2. 完整解压 ZIP。
3. 双击 `YUCEdu双向转换器.exe`。
4. 选择“解密”或“加密”。
5. 点击“选择文件夹”决定本次输出位置。
6. 添加文件并开始处理。

```text
选择模式 → 选择输出文件夹 → 添加文件 → 开始处理
```

## 从源码运行

要求：Python 3.11 或更高版本。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m yucedu_converter
```

## 测试

公开测试套件不包含真实课程媒体。

```powershell
$env:PYTHONPATH = "$PWD\src"
python -X utf8 -m unittest discover -s tests -v
```

配置本地真实样本后可以运行完整回归：

```powershell
$env:YUCEDU_REGRESSION_SAMPLE = "<样本路径>/样本.yucedu"
python -X utf8 -m unittest discover -s tests -v
```

当前本地完整回归结果：20 项通过。

## Windows 构建

```powershell
python -m pip install -e ".[build]"
.\scripts\build_windows.ps1
```

构建输出：

```text
dist\YUCEdu双向转换器\
```

生成正式 ZIP：

```powershell
.\scripts\package_release.ps1
```

## 当前兼容范围

| 项目 | 状态 |
|---|---|
| Windows 10/11 x64 | 已验证 |
| 解密 `.yucedu` | 已验证配置支持 |
| 普通视频反向加密 | 已验证配置支持 |
| WinNetPlayer1018 播放 | 已完成样本验证 |
| macOS 原播放器研究 | 已建立本地参考报告 |
| macOS 原生版本 | 路线图阶段 |
| Linux / Android / iOS | 路线图阶段 |

不同来源的 `.yucedu` 可能使用不同配置。项目通过明确的资源校验和回归测试维护当前已验证配置。

## 上游参考资料

- [网络播放器下载中心](https://www.drmsoft.cn/playernetN7.2/down.asp)
- [Windows 播放器下载地址](https://fuwu2.drmsoft.net/drmsoft/WinNetPlayer1018.zip)
- [macOS 播放器下载地址](https://fuwu2.drmsoft.net/player/N7.2/MacNetPlayerN7.2.zip)

原播放器、Mac 应用和真实媒体保存在仓库外；仓库只记录公开来源、结构、哈希和兼容测试结论。

## 项目文档

- [使用说明](docs/使用说明.md)
- [项目结构、技术栈与路径规范](docs/项目结构.md)
- [更新日志](docs/更新日志.md)
- [第三方组件](docs/第三方组件.md)
- [参与贡献](.github/CONTRIBUTING.md)
- [安全说明](.github/SECURITY.md)
- [转换格式说明](docs/格式说明.md)
- [Windows 构建说明](docs/构建说明.md)
- [发布包目录说明](docs/发布说明.md)
- [测试与兼容报告](docs/兼容报告.md)
- [多平台路线图](docs/路线图.md)
- [上游播放器来源](docs/研究/上游来源.md)
- [MacNetPlayer 本地分析](docs/研究/Mac播放器.md)

## 路线图

1. 发布 Windows 2.0.1 源码和 Release。
2. 增加格式检查和命令行工具。
3. 建立跨平台共享核心与固定测试向量。
4. 支持 macOS Intel 与 Apple Silicon。
5. 支持 Linux、Android 和 iOS。

## 许可证

项目源码使用 [MIT License](LICENSE)。第三方组件信息见 [第三方组件说明](docs/第三方组件.md)。
