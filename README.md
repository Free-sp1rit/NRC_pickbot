# pickbot

Python-based foreground automation bot for Windows games.

This version is focused on foreground input only and is driven entirely by `config.json`.

## What this does

- Brings the target game window to the foreground.
- Sends keyboard and mouse input with `pyautogui`.
- Supports three primitive actions:
  - `mouse_click`
  - `mouse_hold`
  - `key_tap`
- Runs a step-by-step workflow from `config.json`.
- Uses hotkeys to start, stop, reload config, and exit.
- Writes logs to `logs/pickbot.log`.

## Requirements

- Windows
- Python 3.10+

## Install

On Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

If your repo is in WSL, you can still open it from Windows here:

`\\wsl.localhost\Ubuntu\home\yimg\code\pickbot`

## Run

```powershell
python pickbot.py
```

Default hotkeys:

- `F8`: start or stop
- `F9`: reload `config.json`
- `F10`: exit

## Config

The bot reads `config.json`.

Minimal example:

```json
{
  "target": {
    "process_name": "NRC-Win64-Shipping.exe",
    "bring_to_front": true
  },
  "runtime": {
    "idle_poll_seconds": 0.2,
    "cycle_delay_seconds": 0.0
  },
  "safety": {
    "mouse_corner_stop": true,
    "corner_size": 5
  },
  "steps": [
    {
      "type": "mouse_hold",
      "position": "cursor",
      "button": "left",
      "hold_seconds": 0.02,
      "after_seconds": 1.0
    }
  ]
}
```

Supported step types:

- `key_tap`: keyboard single tap
- `mouse_click`: mouse single click
- `mouse_hold`: mouse press and hold, default 20ms

Common step fields:

- `repeat`: repeat count for the step
- `repeat_interval_seconds`: delay between repeats inside one step
- `after_seconds`: delay after the step finishes

Mouse step fields:

- `position: "cursor"`: use the current mouse position
- `x` / `y`: fixed click point
- `relative_to_window`: treat `x` and `y` as window-relative coordinates
- `button`: `left`, `right`, `middle`
- `hold_seconds`: only used by `mouse_hold`, defaults to `0.02`

Keyboard step fields:

- `key`: key name such as `p`, `space`, `f1`
- `hold_seconds`: key down duration, defaults to `0.03`

## Notes

- This is foreground automation, so it will take focus and interfere with normal keyboard and mouse use while running.
- Start with the game in windowed or borderless mode while testing.
- Some games with anti-cheat may detect or block automation.
- Emergency stop: move the mouse to the top-left corner of the screen.

## Build EXE

Windows-side build:

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

WSL-to-Windows release:

```bash
./release_wsl.sh
```

That release flow builds on Windows and publishes to:

`G:\MyBot\pickbot`

Final release files are intended to be:

- `pickbot.exe`
- `config.json`
- `README.md`
- `USER_GUIDE.md`
