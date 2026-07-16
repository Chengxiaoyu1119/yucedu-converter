# yucedu-converter 首次公开仓库设计

## 目标

把已经通过测试的 Windows 2.0.1 双向转换器整理为公开 GitHub 项目 `yucedu-converter`，建立可复现的源码结构、自动测试、Windows 构建流程和 `v2.0.1` Release。

## 固定决策

- 本地 Git 根目录：当前检出的 `<project-root>` 目录。
- GitHub 仓库名：`yucedu-converter`。
- 仓库可见性：公开。
- 许可证：MIT。
- 默认分支：`main`。
- 首次标签与 Release：`v2.0.1`。
- 首发平台：Windows 10/11 x64。
- Python 包名：`yucedu_converter`。
- Git 仓库只保存源码、测试、文档、构建配置和运行必需的小型资源。

## 第一目标范围

第一目标只完成当前 Windows 版本上线：

- 解密 `.yucedu` 为普通视频。
- 把常见视频加密为 `.yucedu`。
- 批量文件和文件夹任务。
- 手动选择输出文件夹。
- 现代自动隐藏滚动条。
- 进度、取消、自动改名和播放器适配。
- 20 项本地自动测试。
- GitHub Actions 自动测试和 Windows 构建。
- GitHub Release 发布 ZIP 与 SHA256。

macOS、Linux、Android、iOS 的实现放入后续里程碑，不扩大首次上线变更面。

## 仓库结构

```text
yucedu-converter/
├─ .github/
│  ├─ ISSUE_TEMPLATE/
│  └─ workflows/
├─ src/yucedu_converter/
│  └─ resources/
├─ tests/fixtures/
├─ packaging/windows/
├─ scripts/
├─ docs/
│  ├─ images/
│  ├─ research/
│  └─ superpowers/
├─ .editorconfig
├─ .gitattributes
├─ .gitignore
├─ CHANGELOG.md
├─ CONTRIBUTING.md
├─ LICENSE
├─ README.md
├─ SECURITY.md
├─ THIRD_PARTY_NOTICES.md
└─ pyproject.toml
```

## 源码迁移

现有 `app` 包迁移为 `src/yucedu_converter`：

- `app/converter_core.py` → `src/yucedu_converter/converter.py`。
- `app/gui.py` → `src/yucedu_converter/gui.py`。
- `app/main.py` → `src/yucedu_converter/main.py`。
- `launcher.py` → `src/yucedu_converter/__main__.py`。
- 资源文件改为英文技术文件名，避免构建工具输出乱码。
- 测试导入路径统一为 `yucedu_converter`。

真实回归样本继续留在本地。公开仓库中的真实样本回归测试通过环境变量 `YUCEDU_REGRESSION_SAMPLE` 选择文件；CI 未配置该变量时跳过此项，其余测试正常运行。

## 公开与本地边界

仓库排除：

- `WinNetPlayer1018.exe`。
- `MacNetPlayer.app`。
- 真实 `.yucedu` 文件。
- 普通视频。
- 解密结果。
- 构建缓存、日志和正式 ZIP。

仓库保留：

- 运行需要的 8,192 字节尾部表。
- 运行需要的 7,688 字节兼容尾部。
- 应用 ICO。
- 资源长度和 SHA256 校验逻辑。
- 上游播放器来源、版本、文件结构与哈希研究文档。

## macOS 参考资料

`MacNetPlayer.app` 只作为本地兼容研究输入。公开文档记录：

- 主程序为 64 位 Intel x86_64 Mach-O。
- Bundle 内部版本为 1.0.0。
- 包含 FFmpeg 和 SDL2 动态库。
- 官方下载页使用 N7.2 产品标签。
- 官方页面标注 macOS 运行环境为 OS X 10.12+。

## 自动化

`test-windows.yml` 在 push 和 pull request 时：

1. 使用 Windows runner 和 Python 3.13。
2. 安装项目测试依赖。
3. 运行 `python -m unittest discover -s tests -v`。

`release-windows.yml` 在推送 `v*` 标签时：

1. 运行测试。
2. 使用 PyInstaller 构建 onedir 程序。
3. 生成 ZIP。
4. 生成 SHA256。
5. 上传 GitHub Actions artifact。

首次 `v2.0.1` Release 使用已在本机验证的正式 ZIP 和 SHA256；后续版本由工作流持续构建。

## README

README 包含：

- 项目用途和状态。
- Windows GUI 截图。
- 功能列表。
- 快速使用步骤。
- 支持格式。
- 安装与源码运行方式。
- 测试和构建命令。
- 上游播放器参考来源。
- 多平台路线图。
- Release 下载入口。

## 完成标准

- 本地根目录名为 `yucedu-converter`。
- 本地测试通过。
- 本地 Windows 构建通过。
- Git 状态干净。
- GitHub 公开仓库可访问。
- `main` 分支包含完整源码与文档。
- Actions 测试通过。
- `v2.0.1` 标签可见。
- `v2.0.1` Release 附加 ZIP 和 SHA256。
- 仓库扫描确认没有原播放器、Mac 应用和真实视频样本。
