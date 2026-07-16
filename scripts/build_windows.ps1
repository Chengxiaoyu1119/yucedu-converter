$ErrorActionPreference = 'Stop'

$ProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$DistRoot = Join-Path $ProjectRoot 'dist'
$WorkRoot = Join-Path $ProjectRoot 'build'
$SpecPath = Join-Path $ProjectRoot 'packaging\windows\yucedu-converter.spec'
$env:PYTHONPATH = Join-Path $ProjectRoot 'src'
$PythonExecutable = (Get-Command python -ErrorAction Stop).Source
$PythonRoot = Split-Path -Parent $PythonExecutable
$PythonLibraryBin = Join-Path $PythonRoot 'Library\bin'
if (Test-Path -LiteralPath $PythonLibraryBin -PathType Container) {
    $env:PATH = "$PythonLibraryBin;$env:PATH"
}

Write-Host "项目目录：$ProjectRoot"
Write-Host "Python：$PythonExecutable"
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

Write-Host "构建成功：$ExePath"
