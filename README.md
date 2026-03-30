# pickbot

Python-based foreground automation bot for Windows games.

This version is focused on foreground input only and uses:

- `config.json` for project settings and default values
- `flow.txt` for the short editable action flow

## What this does

- Brings the target game window to the foreground.
- Sends keyboard and mouse input with `pyautogui`.
- Supports four primitive actions:
  - `mouse_click`
  - `mouse_hold`
  - `key_tap`
  - `wait`
- Inserts a default wait between every two steps.
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
- `F9`: reload `config.json` and `flow.txt`
- `F10`: exit

## Config Layout

The bot reads project settings from `config.json` and workflow steps from `flow.txt`.

### config.json

Use `config.json` for stable project settings and default step parameters.

```json
{
  "target": {
    "process_name": "NRC-Win64-Shipping.exe",
    "window_title_contains": "",
    "bring_to_front": true
  },
  "runtime": {
    "idle_poll_seconds": 0.2,
    "cycle_delay_seconds": 0.0
  },
  "workflow": {
    "path": "flow.txt",
    "default_between_seconds": 1.0
  },
  "defaults": {
    "mouse_click": {
      "position": "center",
      "button": "left"
    },
    "mouse_hold": {
      "position": "center",
      "button": "left",
      "hold_seconds": 0.02
    },
    "key_tap": {
      "key": "p",
      "hold_seconds": 0.03
    },
    "wait": {
      "seconds": 1.0
    }
  }
}
```

### flow.txt

Use `flow.txt` for the step order.

```txt
# Default gap between steps comes from config.json
hold position=cursor
key p gap=0.5
click x=960 y=540
wait 2
```

## Flow Syntax

Supported steps:

- `click`: mouse single click
- `hold`: mouse hold, default 20ms
- `key`: keyboard single tap
- `wait`: explicit wait step
- `repeat`: run a block a fixed number of times, then close it with `end`
- `for_seconds`: keep running a block until the duration is reached, then close it with `end`

Common per-step overrides:

- `gap=0.5`: wait time before the next step, overriding `workflow.default_between_seconds`
- `repeat=3`
- `repeat_interval_seconds=0.05`

Mouse overrides:

- `position=center|cursor|window_center`
- `x=960 y=540`
- `base=2560x1440`: scale coordinates from a base resolution to the current screen resolution
- `relative_to_window=true|false`
- `button=left|right|middle`
- `hold_ms=20` or `hold_seconds=0.02`

Keyboard overrides:

- `key p`
- `hold_ms=30` or `hold_seconds=0.03`

Timed block example:

```txt
for_seconds 30
key tab
wait 15
end
```

Count block example:

```txt
repeat 30
key tab
key 2
end
```

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
- `flow.txt`
- `README.md`
- `USER_GUIDE.md`
