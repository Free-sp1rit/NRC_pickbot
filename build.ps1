param(
    [string]$InputScript = (Join-Path $PSScriptRoot "pickbot.ahk"),
    [string]$OutputDir = $PSScriptRoot,
    [string]$OutputName = "pickbot.exe"
)

$toolSourceDir = Join-Path $PSScriptRoot "compile"
$sourceCompiler = Join-Path $toolSourceDir "Ahk2Exe.exe"
$sourceRuntime = Join-Path $toolSourceDir "AutoHotkey.exe"
$toolRoot = Join-Path $PSScriptRoot "_compile_runtime"
$toolCompilerDir = Join-Path $toolRoot "Compiler"
$compiler = Join-Path $toolCompilerDir "Ahk2Exe.exe"

if (-not (Test-Path $sourceCompiler)) {
    throw "Ahk2Exe.exe was not found at $sourceCompiler."
}

if (-not (Test-Path $sourceRuntime)) {
    throw "AutoHotkey.exe was not found at $sourceRuntime."
}

$runtimeVersion = (Get-Item $sourceRuntime).VersionInfo.ProductVersion
if ($runtimeVersion -match "-a") {
    throw "AutoHotkey.exe at $sourceRuntime is an alpha build ($runtimeVersion). Replace it with a stable AutoHotkey v2 release."
}

if (-not (Test-Path $InputScript)) {
    throw "Input script not found: $InputScript"
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $toolRoot
New-Item -ItemType Directory -Force -Path $toolCompilerDir | Out-Null

Copy-Item -Path $sourceRuntime -Destination (Join-Path $toolRoot "AutoHotkey.exe") -Force
Copy-Item -Path $sourceCompiler -Destination $compiler -Force

$outputPath = Join-Path $OutputDir $OutputName

try {
    & $compiler /in $InputScript /out $outputPath

    if ($LASTEXITCODE -ne 0) {
        throw "Ahk2Exe exited with code $LASTEXITCODE."
    }

    if (-not (Test-Path $outputPath)) {
        throw "Failed to compile: $InputScript"
    }

    Write-Host "Built: $outputPath"
}
finally {
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $toolRoot
}
