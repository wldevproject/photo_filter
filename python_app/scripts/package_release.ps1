param(
    [string]$ProductVersion = "1.0.0",
    [string]$ReleaseDir = "release",
    [switch]$BuildIfMissing
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$exePath = Join-Path $projectRoot "dist\\photo_sorter.exe"
$msiPath = Join-Path $projectRoot "dist\\photo_sorter.msi"

if ((-not (Test-Path $exePath)) -or (-not (Test-Path $msiPath))) {
    if ($BuildIfMissing) {
        & (Join-Path $PSScriptRoot "build_all.ps1") -ProductVersion $ProductVersion
    } else {
        throw "File build belum lengkap. Pastikan $exePath dan $msiPath sudah ada, atau pakai -BuildIfMissing."
    }
}

$releaseFullPath = if ([System.IO.Path]::IsPathRooted($ReleaseDir)) {
    $ReleaseDir
} else {
    Join-Path $projectRoot $ReleaseDir
}

if (-not (Test-Path $releaseFullPath)) {
    New-Item -ItemType Directory -Path $releaseFullPath -Force | Out-Null
}

$releaseExe = Join-Path $releaseFullPath "photo_sorter.exe"
$releaseMsi = Join-Path $releaseFullPath "photo_sorter.msi"

Copy-Item $exePath $releaseExe -Force
Copy-Item $msiPath $releaseMsi -Force

$archiveName = "photo_sorter_${ProductVersion}_windows_x64.zip"
$archivePath = Join-Path $releaseFullPath $archiveName

if (Test-Path $archivePath) {
    Remove-Item $archivePath -Force
}

Compress-Archive -Path $releaseExe, $releaseMsi -DestinationPath $archivePath

Write-Host "Release files siap:"
Write-Host "- $releaseExe"
Write-Host "- $releaseMsi"
Write-Host "- $archivePath"
