# 测试样本说明

公开仓库只接收自行生成的合成测试数据。真实课程视频、原播放器文件、账号资料和本地 `.yucedu` 样本保存在仓库外。

本地完整回归测试通过环境变量指定样本：

```powershell
$env:YUCEDU_REGRESSION_SAMPLE = "<样本路径>/样本.yucedu"
python -X utf8 -m unittest discover -s tests -v
```

未设置该变量时，真实样本回归项显示为跳过，其余测试继续执行。
