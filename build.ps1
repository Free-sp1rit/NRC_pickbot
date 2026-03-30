param(
    [string]$PythonCommand = "python",
    [string]$VenvDir = (Join-Path $PSScriptRoot ".venv-build"),
    [string]$BuildDir = (Join-Path $PSScriptRoot "build"),
    [string]$DistDir = (Join-Path $PSScriptRoot "dist")
)

$ErrorActionPreference = "Stop"

$venvPython = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    & $PythonCommand -m venv $VenvDir
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
& $venvPython -m pip install pyinstaller

Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $BuildDir
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $DistDir
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
New-Item -ItemType Directory -Force -Path $DistDir | Out-Null

Push-Location $PSScriptRoot
try {
    & $venvPython -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --console `
        --name pickbot `
        --specpath $BuildDir `
        --distpath $DistDir `
        --workpath $BuildDir `
        --collect-all cv2 `
        --hidden-import win32gui `
        --hidden-import win32con `
        --hidden-import win32process `
        (Join-Path $PSScriptRoot "pickbot.py")
}
finally {
    Pop-Location
}

$exePath = Join-Path $DistDir "pickbot.exe"
if (-not (Test-Path $exePath)) {
    throw "Build finished without producing $exePath"
}

Write-Host "Built: $exePath"
