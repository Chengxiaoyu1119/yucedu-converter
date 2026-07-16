# MacNetPlayer 本地分析

本地参考路径：

```text
<研究资料目录>/macos/MacNetPlayer.app
```

该路径只用于本地研究，不属于 Git 仓库内容。

## Bundle 信息

```text
CFBundleName：MacNetPlayer
CFBundleDisplayName：MacNetPlayer
CFBundleIdentifier：MacNetPlayer
CFBundleExecutable：MacNetPlayer
CFBundleShortVersionString：1.0.0
CFBundleVersion：1.0.0
LSMinimumSystemVersion：10.9
Bundle 文件数：13
Bundle 总大小：43,458,308 字节
```

官方下载文件名使用 `MacNetPlayerN7.2.zip`，Bundle 内部版本为 `1.0.0`。兼容矩阵同时记录这两个版本标识。

## 主程序

```text
文件：Contents/MacOS/MacNetPlayer
格式：Mach-O 64 位
架构：Intel x86_64
大小：20,046,544 字节
SHA256：5b8d395dd7086fffA87ca68f1d7252303b85bc9badd479748ac86c5b65a3ef52
```

## 媒体组件

Bundle 包含：

```text
libavcodec.dylib
libavdevice.dylib
libavfilter.dylib
libavformat.dylib
libavutil.dylib
libswresample.dylib
libswscale.dylib
libSDL2.dylib
libSDL2_mixer.dylib
```

这组文件表明播放器采用 FFmpeg 与 SDL2 类媒体管线。主程序还引用 AVFoundation、CoreMedia、Metal、MetalKit、CoreAudio 和 JavaScriptCore 等 macOS 框架。

## 后续测试目标

- 在 Intel macOS 上记录启动与文件打开流程。
- 在 Apple Silicon 上验证运行方式。
- 对同一 `.yucedu` 文件执行 Windows 与 macOS 播放对比。
- 对重新加密结果执行跨播放器一致性测试。
