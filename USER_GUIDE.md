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

## Important notes

- This is foreground automation and will take control of keyboard and mouse input while running.
- The game should be in windowed or borderless mode during setup and testing.
- Template images should be placed in the `templates/` folder.
- The old AutoHotkey files are kept only as legacy tooling.
