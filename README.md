# pickbot

Minimal AutoHotkey v2 MVP for sending scripted key and mouse input to a target window without using screenshots.

## What this does

- Targets a specific window with `ControlSend` and `ControlClick`.
- Runs a fixed loop of steps from `config.ini`.
- Uses hotkeys to start, stop, reload config, and exit.
- Writes a plain text log to `logs/pickbot.log`.

## What this does not do

- No screenshot recognition.
- No computer vision.
- No dynamic pathfinding or state detection.
- No bypass for anti-cheat or exclusive input models.

If the game only accepts raw or exclusive foreground input, background delivery may not work.

## Requirements

- Windows
- AutoHotkey v2

## Run from Win11

This repository currently lives in WSL. On your Windows 11 side, the same folder is available at:

`\\wsl.localhost\Ubuntu\home\yimg\code\pickbot`

You can run the bot in either of these ways:

1. Install AutoHotkey v2 on Windows.
2. Open the folder above in Explorer.
3. Edit `config.ini`.
4. Run the script:
   - Double-click `pickbot.ahk`, or
   - Right-click `pickbot.ahk` and choose Run Script, or
   - Run `powershell -ExecutionPolicy Bypass -File .\run.ps1`

The simplest path is to leave the source code in WSL and only execute it from Windows.

## Release to G Drive

This repo includes a WSL-side release script which only copies runtime files to:

`G:\MyBot\pickbot`

From WSL, run:

```bash
./release_wsl.sh
```

It stages the build in the target directory, compiles the executable there, and leaves only these release artifacts:

- `pickbot.exe`
- `config.ini`
- `USER_GUIDE.md`
- `README.md`

It does not modify any other Windows directory.

## Quick start

1. Install AutoHotkey v2.
2. Edit `config.ini`.
3. Change `WinTitle` to your game window rule, for example:
   - `ahk_exe NRC-Win64-Shipping.exe`
   - `Game Window Title`
4. Run `pickbot.ahk`.
5. Use the hotkeys:
   - `F8`: start or stop the loop
   - `F9`: reload `config.ini`
   - `F10`: exit

## Build an EXE

You can package the script as an `.exe`.

- Windows Explorer:
  - Right-click `pickbot.ahk`
  - Choose `Compile Script`
- PowerShell:
  - Run `powershell -ExecutionPolicy Bypass -File .\build.ps1`

For the release flow used by this repo, run `build.ps1` from `G:\MyBot\pickbot`.
It writes the final executable directly into that same folder:

- `G:\MyBot\pickbot\pickbot.exe`

For the default release workflow, use `./release_wsl.sh` in WSL. It compiles in place and then removes temporary build files from the Windows release folder.

Important:

- The compiled EXE does not improve compatibility with anti-cheat or games which reject background input.
- The EXE still reads `config.ini` from its own directory, so keep `config.ini` next to `pickbot.exe`.
- Compiling is mainly for convenience and distribution. It is not a stealth feature.

## Config format

The script reads these sections:

```ini
[Target]
WinTitle=ahk_exe NRC-Win64-Shipping.exe

[Loop]
IntervalMs=3000

[Step1]
Type=Key
Value=1
DelayMs=500

[Step2]
Type=Click
X=100
Y=100
Button=Left
Count=1
DelayMs=800
```

Supported step types:

- `Key`: sends a key sequence such as `1`, `{Space}`, `{F1}`
- `Text`: sends literal text
- `Click`: clicks a coordinate in the target window client area
- `Sleep`: pauses inside the loop for `DurationMs`

## Notes

- `ControlClick` uses `NA` mode and `SetControlDelay -1` to reduce focus stealing.
- This MVP is best for deterministic timed tasks.
- Start with the game in windowed or borderless mode while testing.
- If Windows warns about running files directly from `\\wsl.localhost\...`, use the released folder `G:\MyBot\pickbot` instead.
