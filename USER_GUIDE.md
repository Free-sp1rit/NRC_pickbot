# pickbot User Guide

## Current runtime

The primary runtime is Python.

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
- `F9`: reload `config.json` and `flow.txt`
- `F10`: exit

## Emergency stop

- Move the mouse to the top-left corner of the screen to stop the running bot loop.

## Important notes

- This is foreground automation and will take control of keyboard and mouse input while running.
- The game should be in windowed or borderless mode during setup and testing.
- The current program uses four action types: `mouse_click`, `mouse_hold`, `key_tap`, and `wait`.
- `mouse_hold` defaults to 20ms if you do not override `hold_seconds`.
- There is a default wait between every two steps. You can change it in `config.json`.
- `for_seconds ... end` can be used for a timed sub-loop.
- `repeat ... end` can be used for a count-based sub-loop.
- `base=2560x1440` can scale coordinates from a fixed reference resolution.
- `flow.txt` is intentionally short. Example:

```txt
hold position=cursor
key p gap=0.5
wait 1.5
click x=960 y=540
```
