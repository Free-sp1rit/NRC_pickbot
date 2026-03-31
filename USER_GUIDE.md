# pickbot User Guide

## Current runtime

The primary runtime is Python.

## Official release notice

- Official builds are intended to be distributed free of charge.
- Use only the official release channel.
- If you bought this tool from an unofficial source, request a refund.
- Only official builds with a published version and checksum are supported.

## How to use

1. Install Python 3.10 or newer on Windows.
2. Install the dependencies from `requirements.txt`.
3. Edit `config.json` for project settings.
4. Edit `flow.txt` for the action sequence.
5. Run:

```powershell
python pickbot.py
```

## Default hotkeys

- `F8`: start or stop
- `F9`: reload the main `config.json` and `flow.txt`
- `F7`: load `flow_test.txt`
- `F10`: exit

## Emergency stop

- Move the mouse to the top-left corner of the screen to stop the running bot loop.

## Important notes

- This is foreground automation and will take control of keyboard and mouse input while running.
- The game should be in windowed or borderless mode during setup and testing.
- This tool uses simulated keyboard and mouse input plus screen-state detection.
- This tool does not directly read or write the target program's memory.
- The current program uses actions like `mouse_click`, `mouse_hold`, `mouse_drag`, `key_tap`, and `wait`.
- `mouse_hold` defaults to 20ms if you do not override `hold_seconds`.
- `drag_down_half position=cursor` means hold the mouse, drag downward by half the screen height, then release.
- `mouse_drag` defaults to finishing the drag in `0.5s`.
- There is a default wait between every two steps. You can change it in `config.json`.
- `for_seconds ... end` can be used for a timed sub-loop.
- `repeat ... end` can be used for a count-based sub-loop.
- `wait_pixel` can be used for lightweight state detection.
- `wait_image` can be used for scene detection based on a reference screenshot region.
- `base=2560x1440` can scale coordinates from a fixed reference resolution.
- `flow.txt` is intentionally short. Example:
- `flow_test.txt` is a separate test workflow file for quick action tests.

```txt
hold position=cursor
key p gap=0.5
wait 1.5
click x=960 y=540
```

## Release files

An official release may include:

- `pickbot.exe`
- `config.json`
- `flow.txt`
- `USER_GUIDE.md`
- `README.md`
- `NOTICE.txt`
- `VERSION.txt`
- `SHA256SUMS.txt`
