# pickbot User Guide

## Current runtime

The primary runtime is now Python, not AutoHotkey.

## How to use

1. Install Python 3.10 or newer on Windows.
2. Install the dependencies from `requirements.txt`.
3. Edit `config.json`.
4. Run:

```powershell
python pickbot.py
```

## Default hotkeys

- `F8`: start or stop
- `F9`: reload `config.json`
- `F10`: exit

## Emergency stop

- Move the mouse to the top-left corner of the screen to stop the running bot loop.

## Important notes

- This is foreground automation and will take control of keyboard and mouse input while running.
- The game should be in windowed or borderless mode during setup and testing.
- The current program only uses three action types: `mouse_click`, `mouse_hold`, and `key_tap`.
- `mouse_hold` defaults to 20ms if you do not override `hold_seconds`.
