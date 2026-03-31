param(
    [string]$PythonCommand = "python",
    [string]$VenvDir = (Join-Path $PSScriptRoot ".venv-build"),
    [string]$BuildDir = (Join-Path $PSScriptRoot "build"),
    [string]$DistDir = (Join-Path $PSScriptRoot "dist"),
    [string]$VersionFile = (Join-Path $PSScriptRoot "VERSION.txt")
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

$versionText = "unknown"
if (Test-Path $VersionFile) {
    $versionText = (Get-Content -Raw -Path $VersionFile).Trim()
    Set-Content -Path (Join-Path $DistDir "VERSION.txt") -Value $versionText -Encoding utf8
}

$checksumLines = @()
$filesToHash = @("pickbot.exe", "VERSION.txt")
foreach ($fileName in $filesToHash) {
    $filePath = Join-Path $DistDir $fileName
    if (Test-Path $filePath) {
        $hash = (Get-FileHash -Algorithm SHA256 -Path $filePath).Hash.ToLowerInvariant()
        $checksumLines += "$hash *$fileName"
    }
}

if ($checksumLines.Count -gt 0) {
    Set-Content -Path (Join-Path $DistDir "SHA256SUMS.txt") -Value $checksumLines -Encoding ascii
}

Write-Host "Built: $exePath"
Write-Host "Version: $versionText"
