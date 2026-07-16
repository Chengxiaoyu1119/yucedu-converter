# 参与贡献

这份文档规定源码、文档、路径和提交的维护方式。目标是让项目在继续开发时保持简单、可读，并避免把本机资料带入公开仓库。

## 开发环境

要求 Python 3.11 或更高版本。虚拟环境是项目专用的 Python 运行空间，可避免依赖影响系统中的其他程序。

Windows：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[build]"
```

macOS：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[macos]"
```

## 目录职责

- `src/yucedu_converter/`：正式程序源码与随程序打包的资源。
- `tests/`：自动测试和公开的合成测试说明。
- `docs/`：用户说明、开发说明、研究记录和界面图片。
- `packaging/windows/`：PyInstaller 的 Windows 打包配置。
- `packaging/macos/`：PyInstaller 的 macOS App 打包配置。
- `scripts/`：构建、发布和项目检查脚本。
- `.github/`：Issue、Pull Request、持续集成和社区规范。
- `local/`：本机样本与参考播放器；整个目录不提交 Git。

目录的完整说明见 [`docs/项目结构.md`](../docs/项目结构.md)。

## 命名规范

- Python 包、模块、函数和变量使用小写英文与下划线，例如 `output_path`。
- Python 类使用英文大驼峰命名，例如 `ConversionResult`。
- 框架入口、配置键、GitHub 工作流和 URL 路径保持英文，避免工具兼容问题。
- 用户直接看到的界面文案、交付文档和说明标题优先使用中文。
- 新文件应放入对应职责目录，不在仓库根目录临时堆放。
- 不创建名称含“最终版”“最新版”“复制”等含义不清的文件；版本通过 Git 标签和更新日志管理。

## 路径与隐私规范

- 源码、文档和配置只记录仓库相对路径、环境变量或示例占位符。
- 不提交个人绝对路径、账号、密码、令牌、设备名称或其他个人资料。
- 不提交原播放器、真实课程媒体、解密输出、日志、构建目录和发布压缩包。
- 本机资料统一放在 `local/fixtures/` 或 `local/players/`。
- `build/`、`dist/` 和 `release/` 是可重新生成的目录，不属于源码。

## 代码修改规范

- 一个修改只解决一个清晰问题，避免顺手改动无关功能。
- 保持现有 `src` 布局；导入统一从 `yucedu_converter` 包开始。
- 转换逻辑放在 `converter.py`，界面逻辑放在 `gui.py`，播放器调用放在 `player.py`，设置持久化放在 `settings.py`，样式放在 `theme.py`。
- 运行时资源统一放在 `src/yucedu_converter/resources/`，并同步检查 `pyproject.toml` 与两个平台的 PyInstaller 配置。
- 程序版本只修改 `src/yucedu_converter/__init__.py` 中的 `APP_VERSION`，其余构建元数据由脚本生成。
- 新增或升级第三方依赖时，更新 `pyproject.toml` 和 `docs/第三方组件.md`，并说明版本选择原因。
- 用户可见行为发生变化时，同步更新 README、对应使用文档和 `docs/更新日志.md`。

## 验证方式

公开测试套件不包含真实课程媒体：

```powershell
$env:PYTHONPATH = "$PWD\src"
python -X utf8 -m unittest discover -s tests -v
```

需要本机回归时，通过环境变量选择 `local/` 中的样本：

```powershell
$env:YUCEDU_REGRESSION_SAMPLE = "$PWD\local\fixtures\regression.yucedu"
python -X utf8 -m unittest discover -s tests -v
```

## Git 提交规范

建议使用“类型 + 简短说明”的提交信息，让历史记录容易理解：

- `feat:` 新功能。
- `fix:` 问题修复。
- `docs:` 只修改文档。
- `refactor:` 调整内部结构但不改变功能。
- `build:` 构建或发布配置。
- `chore:` 其他维护工作。

示例：`docs: 精简项目文档路径`

提交前确认：

- Git 状态中只有本次相关文件。
- 没有个人路径、真实媒体、原播放器、日志、缓存或发布文件。
- 文档链接和脚本引用仍指向存在的文件。
- 用户可见变化已经写入对应中文文档。
