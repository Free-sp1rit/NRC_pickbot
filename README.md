# pickbot

Python-based foreground automation bot for Windows games.

This version is designed for games which ignore background window messages and only react to real foreground keyboard and mouse input. It also supports template-based screenshot matching for simple screen-state checks.

## What this does

- Brings the target game window to the foreground.
- Sends keyboard and mouse input with `pyautogui` by default.
- Captures screen regions with `pyautogui` by default.
- Matches templates with OpenCV.
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
  "input": {
    "backend": "pyautogui"
  },
  "capture": {
    "backend": "pyautogui"
  },
  "loop": {
    "interval_seconds": 1.0
  },
  "safety": {
    "mouse_corner_stop": true,
    "corner_size": 5
  },
  "steps": [
    {
      "type": "click",
      "position": "cursor",
      "button": "left"
    }
  ]
}
```

Supported step types:

- `key`: press a foreground key such as `p`, `space`, `f1`
- `click`: click a coordinate, optionally relative to the target window
- `sleep`: wait for a number of seconds
- `wait_image`: poll a region until a template image matches

Backend fields:

- `input.backend`: `pyautogui` or `pydirectinput`
- `capture.backend`: `pyautogui` or `mss`

Click step options:

- `position: "cursor"`: click the current mouse position without remapping
- `x` / `y`: click a fixed point
- `relative_to_window`: when using `x` / `y`, treat them as window-relative coordinates

Example `wait_image` step:

```json
{
  "type": "wait_image",
  "template": "templates/battle_ready.png",
  "region": [100, 100, 300, 200],
  "threshold": 0.92,
  "timeout_seconds": 5.0,
  "relative_to_window": true
}
```

## Template Matching

Put template images in `templates/`.

The `region` field is `[x, y, width, height]`.

- If `relative_to_window` is `true`, the region is relative to the game window.
- If `relative_to_window` is `false`, the region is absolute screen coordinates.

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
- `templates\`
