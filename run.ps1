param(
    [string]$ScriptPath = (Join-Path $PSScriptRoot "pickbot.ahk")
)

$candidates = @(
    "C:\Program Files\AutoHotkey\AutoHotkey.exe",
    "C:\Program Files\AutoHotkey\UX\AutoHotkeyUX.exe",
    (Join-Path $env:LOCALAPPDATA "Programs\AutoHotkey\AutoHotkey.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\AutoHotkey\UX\AutoHotkeyUX.exe")
)

$runner = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $runner) {
    throw "AutoHotkey was not found. Install AutoHotkey v2 on Windows first."
}

if (-not (Test-Path $ScriptPath)) {
    throw "Script not found: $ScriptPath"
}

Start-Process -FilePath $runner -ArgumentList @($ScriptPath) -WorkingDirectory (Split-Path -Parent $ScriptPath)
Write-Host "Started: $ScriptPath"
Write-Host "Runner:  $runner"
