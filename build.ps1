param(
    [string]$InputScript = (Join-Path $PSScriptRoot "pickbot.ahk"),
    [string]$OutputDir = $PSScriptRoot,
    [string]$OutputName = "pickbot.exe"
)

$compilerCandidates = @(
    "C:\Program Files\AutoHotkey\Compiler\Ahk2Exe.exe",
    (Join-Path $env:LOCALAPPDATA "Programs\AutoHotkey\Compiler\Ahk2Exe.exe")
)

$compiler = $compilerCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $compiler) {
    throw "Ahk2Exe.exe was not found. Reinstall AutoHotkey v2 with the compiler, or open AutoHotkey Dash and install Compile support."
}

if (-not (Test-Path $InputScript)) {
    throw "Input script not found: $InputScript"
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$outputPath = Join-Path $OutputDir $OutputName

& $compiler /in $InputScript /out $outputPath

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "Built: $outputPath"
