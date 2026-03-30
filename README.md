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

## Quick start

1. Install AutoHotkey v2.
2. Edit `config.ini`.
3. Change `WinTitle` to your game window rule, for example:
   - `ahk_exe Game.exe`
   - `Game Window Title`
4. Run `pickbot.ahk`.
5. Use the hotkeys:
   - `F8`: start or stop the loop
   - `F9`: reload `config.ini`
   - `F10`: exit

## Config format

The script reads these sections:

```ini
[Target]
WinTitle=ahk_exe notepad.exe

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
