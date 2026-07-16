# 第三方组件说明

本项目源码与 Windows 构建流程使用以下组件：

- Python：Python Software Foundation License。
- Tk / ttk：随 Python 的 Tkinter 运行环境分发。
- cryptography：Apache License 2.0 / BSD 双许可证组件。
- PyInstaller：GPL 2.0 with special exception，用于生成独立程序。

上游参考播放器可能包含 FFmpeg、SDL2 等组件；这些播放器不随本仓库分发。研究文档只记录公开来源、文件结构、版本和哈希。

发布新版本时应同时检查实际打包目录中的第三方许可证元数据。
