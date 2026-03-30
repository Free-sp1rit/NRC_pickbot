param(
    [string]$InputScript = (Join-Path $PSScriptRoot "pickbot.ahk"),
    [string]$OutputDir = $PSScriptRoot,
    [string]$OutputName = "pickbot.exe"
)

$toolSourceDir = Join-Path $PSScriptRoot "compile"
$sourceCompiler = Join-Path $toolSourceDir "Ahk2Exe.exe"
$runtimeCandidates = @(
    (Join-Path $toolSourceDir "AutoHotkey.exe"),
    (Join-Path $toolSourceDir "AutoHotkey64.exe"),
    (Join-Path $toolSourceDir "AutoHotkey32.exe")
)
$sourceRuntime = $runtimeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
$toolCompilerDir = Join-Path $toolSourceDir "Compiler"
$compiler = Join-Path $toolCompilerDir "Ahk2Exe.exe"
$toolBase = $sourceRuntime

if (-not (Test-Path $sourceCompiler)) {
    throw "Ahk2Exe.exe was not found at $sourceCompiler."
}

if (-not $sourceRuntime) {
    throw "AutoHotkey runtime was not found in $toolSourceDir. Expected AutoHotkey.exe or AutoHotkey64.exe."
}

$runtimeVersion = (Get-Item $sourceRuntime).VersionInfo.ProductVersion
if ($runtimeVersion -match "-a") {
    throw "AutoHotkey.exe at $sourceRuntime is an alpha build ($runtimeVersion). Replace it with a stable AutoHotkey v2 release."
}

if (-not (Test-Path $InputScript)) {
    throw "Input script not found: $InputScript"
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
New-Item -ItemType Directory -Force -Path $toolCompilerDir | Out-Null

Copy-Item -Path $sourceCompiler -Destination $compiler -Force

$outputPath = Join-Path $OutputDir $OutputName
$tempOutputPath = Join-Path $OutputDir "_pickbot_build.exe"

try {
    Remove-Item -Force -ErrorAction SilentlyContinue $tempOutputPath

    & $compiler /in $InputScript /out $tempOutputPath /base $toolBase /silent verbose

    if (($null -ne $LASTEXITCODE) -and ("$LASTEXITCODE" -ne "") -and ($LASTEXITCODE -ne 0)) {
        throw "Ahk2Exe exited with code $LASTEXITCODE."
    }

    $outputReady = $false
    foreach ($attempt in 1..20) {
        if (Test-Path $tempOutputPath) {
            $outputReady = $true
            break
        }
        Start-Sleep -Milliseconds 200
    }

    if (-not $outputReady) {
        throw "Failed to compile: $InputScript"
    }

    Move-Item -Force -Path $tempOutputPath -Destination $outputPath
    Write-Host "Built: $outputPath"
}
finally {
    Remove-Item -Force -ErrorAction SilentlyContinue $tempOutputPath
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $toolCompilerDir
}
