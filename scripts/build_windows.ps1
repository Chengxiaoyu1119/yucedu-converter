$ErrorActionPreference = 'Stop'

$ProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$DistRoot = Join-Path $ProjectRoot 'dist'
$WorkRoot = Join-Path $ProjectRoot 'build\windows'
$SpecPath = Join-Path $ProjectRoot 'packaging\windows\yucedu-converter.spec'
$VersionInfoPath = Join-Path $WorkRoot 'version_info.txt'
$env:PYTHONPATH = Join-Path $ProjectRoot 'src'
$PythonExecutable = (Get-Command python -ErrorAction Stop).Source
$PythonRoot = Split-Path -Parent $PythonExecutable
$PythonLibraryBin = Join-Path $PythonRoot 'Library\bin'
if (Test-Path -LiteralPath $PythonLibraryBin -PathType Container) {
    $env:PATH = "$PythonLibraryBin;$env:PATH"
}

Write-Host "项目目录：$ProjectRoot"
Write-Host "Python：$PythonExecutable"
$Version = (& python -X utf8 (Join-Path $ProjectRoot 'scripts\version_tool.py')).Trim()
if ($LASTEXITCODE -ne 0) {
    throw '读取项目版本失败。'
}
Write-Host "项目版本：$Version"

python -X utf8 (Join-Path $ProjectRoot 'scripts\version_tool.py') --write-windows-info $VersionInfoPath | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw '生成 Windows 版本信息失败。'
}
$env:YUCEDU_WINDOWS_VERSION_INFO = $VersionInfoPath

Write-Host '开始运行隐私检查……'
python -X utf8 (Join-Path $ProjectRoot 'scripts\check_privacy.py')
if ($LASTEXITCODE -ne 0) {
    throw '隐私检查未通过，构建已经停止。'
}
Write-Host '开始运行自动测试……'

Push-Location $ProjectRoot
try {
    python -X utf8 -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) {
        throw '自动测试未通过，构建已经停止。'
    }

    Write-Host '开始构建 Windows 独立程序……'
    python -m PyInstaller --clean --noconfirm `
        --distpath $DistRoot `
        --workpath $WorkRoot `
        $SpecPath
    if ($LASTEXITCODE -ne 0) {
        throw 'PyInstaller 构建失败。'
    }
}
finally {
    Pop-Location
}

$ExePath = Join-Path $DistRoot 'YUCEdu双向转换器\YUCEdu双向转换器.exe'
if (-not (Test-Path -LiteralPath $ExePath -PathType Leaf)) {
    throw "构建完成后没有找到主程序：$ExePath"
}
$ProductVersion = (Get-Item -LiteralPath $ExePath).VersionInfo.ProductVersion
if ($ProductVersion -ne $Version) {
    throw "可执行文件版本不一致：项目=$Version，EXE=$ProductVersion"
}

Write-Host '开始运行正式程序冒烟检查……'
python -X utf8 (Join-Path $ProjectRoot 'scripts\smoke_test_gui.py') $ExePath
if ($LASTEXITCODE -ne 0) {
    throw '正式程序启动检查失败。'
}
python -X utf8 (Join-Path $ProjectRoot 'scripts\verify_taskbar_icon.py') $ExePath
if ($LASTEXITCODE -ne 0) {
    throw '任务栏图标检查失败。'
}

Write-Host "构建成功：$ExePath"
