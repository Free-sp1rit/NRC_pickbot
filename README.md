# pickbot

Python-based foreground automation bot for Windows games.

This version is focused on foreground input only and uses:

- `config.json` for project settings and default values
- `flow.txt` for the short editable action flow

## What this does

- Brings the target game window to the foreground.
- Sends keyboard and mouse input with `pyautogui`.
- Supports input actions and scene wait steps:
  - `mouse_click`
  - `mouse_hold`
  - `mouse_drag`
  - `key_tap`
  - `wait`
- Inserts a default wait between every two steps.
- Uses hotkeys to start, stop, reload config, and exit.
- Writes logs to `logs/pickbot.log`.
- Uses simulated keyboard and mouse input plus screen-state detection.
- Does not directly read or write the target program's memory.

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
- `F9`: reload the main `config.json` + `flow.txt`
- `F7`: load `flow_test.txt` for testing
- `F10`: exit

## Release Policy

- Official builds should be distributed free of charge.
- Only official builds with a published version and checksum should be supported.
- This project currently uses external input simulation and screen detection only.
- This project is not designed around target-process memory read/write.

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
    "test_path": "flow_test.txt",
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

Use `flow_test.txt` for temporary test actions you want to load with `F7`.

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
- `drag`: mouse hold + drag + release
- `drag_down_half`: convenience alias for dragging downward by half the screen height
- `key`: keyboard single tap
- `wait`: explicit wait step
- `wait_pixel`: wait until a screen pixel matches a target color
- `wait_image`: wait until a scene/image region matches a reference screenshot
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

Drag overrides:

- `position=center|cursor|window_center`
- `dx=0 dy=300`
- `dx_ratio=0.0 dy_ratio=0.5`
- `duration_seconds=0.5`
- `steps=20`
- `base=2560x1440`

Pixel wait overrides:

- `x=100 y=200`
- `rgb=255,255,255`
- `tolerance=10`
- `check_interval_seconds=0.2`
- `base=2560x1440`
- `relative_to_window=true|false`

Image wait overrides:

- `template=主场景.png`
- `x=1600 y=0 w=760 h=220`
- `confidence=0.9`
- `grayscale=true|false`
- `check_interval_seconds=0.3`
- `base=2560x1440`
- `relative_to_window=true|false`

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

Drag example:

```txt
drag_down_half position=cursor
```

```txt
drag position=cursor dy_ratio=0.5 duration_seconds=0.4
```

Pixel wait example:

```txt
wait_pixel x=2340 y=1340 base=2560x1440 rgb=210,198,120 tolerance=12
```

Image wait example:

```txt
wait_image template=主场景.png x=1600 y=0 w=760 h=220 base=2560x1440 confidence=0.88
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
- `NOTICE.txt`
- `VERSION.txt`
- `SHA256SUMS.txt`

## Release Prep

For release preparation inside the repository:

- Update `VERSION.txt`
- Review [RELEASE_CHECKLIST.md](/home/yimg/code/pickbot/RELEASE_CHECKLIST.md)
- Update [RELEASE_NOTES_v0.1.0.md](/home/yimg/code/pickbot/RELEASE_NOTES_v0.1.0.md) or create a new release note file
