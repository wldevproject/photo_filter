param(
    [string]$ProductVersion = "1.0.0",
    [string]$ProductName = "Photo Sorter",
    [string]$Manufacturer = "photo_filter",
    [string]$UpgradeCode = "{8D60D057-E59C-4A75-BFD1-A3C3343A8D1D}",
    [string]$OutputPath = "dist\\photo_sorter.msi"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

& (Join-Path $scriptDir "build_exe.ps1")
& (Join-Path $scriptDir "build_msi.ps1") `
    -ProductVersion $ProductVersion `
    -ProductName $ProductName `
    -Manufacturer $Manufacturer `
    -UpgradeCode $UpgradeCode `
    -OutputPath $OutputPath
