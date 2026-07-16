# macOS 使用说明

## 选择下载文件

- Apple Silicon（M1、M2、M3、M4 等）：`yucedu-converter-v2.1.0-macos-arm64.dmg`
- Intel Mac：`yucedu-converter-v2.1.0-macos-x64.dmg`

点击屏幕左上角苹果菜单，选择“关于本机”，即可查看芯片类型。

## 安装

1. 打开 DMG。
2. 把 `YUCEdu双向转换器.app` 拖到 DMG 内的 `Applications` 快捷入口。
3. 前往“应用程序”文件夹。
4. 首次启动时按住 Control 点击应用，选择“打开”。

当前公开构建使用临时签名，尚未接入 Apple Developer ID 公证流程，因此首次启动可能显示 Gatekeeper 提示。完成一次“Control 点击 → 打开”后，后续可正常双击启动。

## 转换

1. 选择“解密 YUCEdu”或“加密视频”。
2. 点击“选择文件夹”，决定本次任务输出位置。
3. 添加一个或多个文件。
4. 点击“开始转换”。

输出位置仍由用户每次主动选择，程序不会自动沿用上一次目录。

## 播放器

普通视频支持：

- macOS 默认播放器。
- IINA。
- VLC。
- 设置中选择的其他 `.app` 播放器。

加密后的 `.yucedu` 兼容验证支持：

- `/Applications/MacNetPlayer.app`
- 与转换器放在同一目录的 `MacNetPlayer.app`
- 设置中手动选择的 `MacNetPlayer.app`

若原 MacNetPlayer 只有 Intel 版本，Apple Silicon Mac 可能提示安装 Rosetta；这只影响原播放器，不影响转换器的 arm64 版本。

## 设置和日志

macOS 设置与日志保存在：

```text
~/Library/Application Support/YUCEdu双向转换器/
├─ 设置.json
└─ 日志/
```

应用本体、真实视频和转换结果不会写入 Git 仓库。

## 校验下载文件

在终端进入下载目录后执行：

```bash
shasum -a 256 -c yucedu-converter-v2.1.0-macos-arm64.dmg.sha256.txt
```

Intel 版本将文件名中的 `arm64` 换成 `x64`。
