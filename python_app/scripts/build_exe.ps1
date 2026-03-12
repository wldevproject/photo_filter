param(
    [switch]$SkipInstallDeps,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

function Get-PythonRuntime {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        return [PSCustomObject]@{
            Exe = $py.Source
            PrefixArgs = @("-3")
        }
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return [PSCustomObject]@{
            Exe = $python.Source
            PrefixArgs = @()
        }
    }

    throw "Python tidak ditemukan. Install Python 3.10+ dulu."
}

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$pythonRuntime = Get-PythonRuntime

if (-not $SkipInstallDeps) {
    $pipUpgradeArgs = @()
    $pipUpgradeArgs += $pythonRuntime.PrefixArgs
    $pipUpgradeArgs += @("-m", "pip", "install", "--upgrade", "pip")
    & $pythonRuntime.Exe @pipUpgradeArgs

    $runtimeDepsArgs = @()
    $runtimeDepsArgs += $pythonRuntime.PrefixArgs
    $runtimeDepsArgs += @("-m", "pip", "install", "-r", "requirements.txt")
    & $pythonRuntime.Exe @runtimeDepsArgs

    $buildDepsArgs = @()
    $buildDepsArgs += $pythonRuntime.PrefixArgs
    $buildDepsArgs += @("-m", "pip", "install", "-r", "requirements-build.txt")
    & $pythonRuntime.Exe @buildDepsArgs
}

$pyinstallerArgs = @()
$pyinstallerArgs += $pythonRuntime.PrefixArgs
$pyinstallerArgs += @(
    "-m",
    "PyInstaller",
    "--noconfirm",
    "--onefile",
    "--windowed",
    "--name",
    "photo_sorter",
    "--icon",
    "assets\\app_icon.ico",
    "--add-data",
    "assets;assets"
)

if ($Clean) {
    $pyinstallerArgs += "--clean"
}

$pyinstallerArgs += "photo_sorter.py"

& $pythonRuntime.Exe @pyinstallerArgs

$exePath = Join-Path $projectRoot "dist\\photo_sorter.exe"
if (-not (Test-Path $exePath)) {
    throw "Build EXE gagal. File tidak ditemukan: $exePath"
}

Write-Host "EXE berhasil dibuat: $exePath"
