$ErrorActionPreference = 'Stop'

$ProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$DistRoot = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot 'dist\YUCEdu双向转换器'))
$ReleaseRoot = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot 'release'))
$env:PYTHONPATH = Join-Path $ProjectRoot 'src'
$Version = (& python -X utf8 (Join-Path $ProjectRoot 'scripts\version_tool.py')).Trim()
if ($LASTEXITCODE -ne 0) {
    throw '读取项目版本失败。'
}
$AssetBase = "yucedu-converter-v$Version-windows-x64"
$StageRoot = [System.IO.Path]::GetFullPath((Join-Path $ReleaseRoot $AssetBase))
$ZipPath = [System.IO.Path]::GetFullPath((Join-Path $ReleaseRoot "$AssetBase.zip"))
$ZipHashPath = "$ZipPath.sha256.txt"
$RuntimeName = '运行组件'
$DocumentRoot = Join-Path $StageRoot '文档'
$PreviewRoot = Join-Path $DocumentRoot '界面预览'

if (-not (Test-Path -LiteralPath $DistRoot -PathType Container)) {
    throw "请先运行 scripts\build_windows.ps1：$DistRoot"
}

New-Item -ItemType Directory -Path $ReleaseRoot -Force | Out-Null
$releasePrefix = $ReleaseRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
foreach ($path in @($StageRoot, $ZipPath, $ZipHashPath)) {
    if (-not $path.StartsWith($releasePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "发布路径越界：$path"
    }
}

if (Test-Path -LiteralPath $StageRoot) {
    Remove-Item -LiteralPath $StageRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $StageRoot | Out-Null
New-Item -ItemType Directory -Path $DocumentRoot | Out-Null
New-Item -ItemType Directory -Path $PreviewRoot | Out-Null

$distRuntime = Join-Path $DistRoot $RuntimeName
if (-not (Test-Path -LiteralPath $distRuntime -PathType Container)) {
    throw "构建目录缺少运行组件：$distRuntime"
}

Copy-Item -LiteralPath (Join-Path $DistRoot 'YUCEdu双向转换器.exe') -Destination $StageRoot
Copy-Item -LiteralPath $distRuntime -Destination $StageRoot -Recurse
Copy-Item -LiteralPath (Join-Path $ProjectRoot 'docs\使用说明.md') -Destination (Join-Path $StageRoot '使用说明.md')
Copy-Item -LiteralPath (Join-Path $ProjectRoot 'docs\发布说明.md') -Destination (Join-Path $DocumentRoot '目录结构.md')
Copy-Item -LiteralPath (Join-Path $ProjectRoot 'docs\更新日志.md') -Destination (Join-Path $DocumentRoot '版本说明.md')
Copy-Item -LiteralPath (Join-Path $ProjectRoot 'LICENSE') -Destination (Join-Path $DocumentRoot 'MIT许可证.txt')
Copy-Item -LiteralPath (Join-Path $ProjectRoot 'docs\第三方组件.md') -Destination (Join-Path $DocumentRoot '第三方组件说明.md')
Get-ChildItem -LiteralPath (Join-Path $ProjectRoot 'docs\images') -File | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $PreviewRoot
}

$coreFiles = @(
    'YUCEdu双向转换器.exe',
    "$RuntimeName\yucedu_converter\resources\aes_tail_table.bin",
    "$RuntimeName\yucedu_converter\resources\compatibility_trailer.bin",
    "$RuntimeName\yucedu_converter\resources\app.ico"
)
$lines = @("YUCEdu 双向转换器 $Version 核心文件 SHA256", '')
foreach ($relative in $coreFiles) {
    $path = Join-Path $StageRoot $relative
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "正式包缺少核心文件：$relative"
    }
    $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    $lines += "$hash  $relative"
}
Set-Content -LiteralPath (Join-Path $StageRoot 'SHA256校验值.txt') -Value $lines -Encoding UTF8

foreach ($path in @($ZipPath, $ZipHashPath)) {
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Force
    }
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $StageRoot,
    $ZipPath,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $true
)

$zipHash = (Get-FileHash -LiteralPath $ZipPath -Algorithm SHA256).Hash.ToLowerInvariant()
[System.IO.File]::WriteAllText($ZipHashPath, "$zipHash  $AssetBase.zip`n", [System.Text.UTF8Encoding]::new($false))

Write-Host "发布目录：$StageRoot"
Write-Host "发布 ZIP：$ZipPath"
Write-Host "校验文件：$ZipHashPath"
Write-Host "ZIP SHA256：$zipHash"
