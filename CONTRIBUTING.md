# 参与贡献

## 开发环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[build]"
```

## 运行测试

```powershell
$env:PYTHONPATH = "$PWD\src"
python -X utf8 -m unittest discover -s tests -v
```

真实样本回归测试通过本地环境变量选择文件：

```powershell
$env:YUCEDU_REGRESSION_SAMPLE = "<样本路径>/样本.yucedu"
```

公开提交只使用合成测试数据。提交前请运行测试，并确认 Git 状态中没有播放器、真实视频、日志、构建缓存和发布压缩包。

## 提交建议

- 一个提交只解决一个清晰问题。
- 用户可见文案优先使用中文。
- Python 包、模块、配置键和 GitHub 工作流使用英文技术名称。
- 新功能同时补充测试和文档。
