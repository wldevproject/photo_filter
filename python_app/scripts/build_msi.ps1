param(
    [string]$ProductVersion = "1.0.0",
    [string]$ProductName = "Photo Sorter",
    [string]$Manufacturer = "photo_filter",
    [string]$UpgradeCode = "{8D60D057-E59C-4A75-BFD1-A3C3343A8D1D}",
    [string]$OutputPath = "dist\\photo_sorter.msi",
    [switch]$BuildExeIfMissing
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$exePath = Join-Path $projectRoot "dist\\photo_sorter.exe"
if (-not (Test-Path $exePath)) {
    if ($BuildExeIfMissing) {
        & (Join-Path $PSScriptRoot "build_exe.ps1")
    } else {
        throw "File EXE belum ada: $exePath`nJalankan .\\scripts\\build_exe.ps1 dulu, atau pakai -BuildExeIfMissing."
    }
}

$wix = Get-Command wix -ErrorAction SilentlyContinue
if (-not $wix) {
    throw "CLI WiX tidak ditemukan. Install dulu lalu pastikan command 'wix' tersedia di terminal."
}

$outputFullPath = if ([System.IO.Path]::IsPathRooted($OutputPath)) {
    $OutputPath
} else {
    Join-Path $projectRoot $OutputPath
}

$outputDir = Split-Path -Parent $outputFullPath
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

$wixArgs = @(
    "build",
    "installer.wxs",
    "-d",
    "ProductVersion=$ProductVersion",
    "-d",
    "ProductName=$ProductName",
    "-d",
    "Manufacturer=$Manufacturer",
    "-d",
    "UpgradeCode=$UpgradeCode",
    "-o",
    $outputFullPath
)

& $wix.Source @wixArgs

if (-not (Test-Path $outputFullPath)) {
    throw "Build MSI gagal. File tidak ditemukan: $outputFullPath"
}

Write-Host "MSI berhasil dibuat: $outputFullPath"
