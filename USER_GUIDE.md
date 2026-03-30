# pickbot User Guide

## Files in the release folder

- `pickbot.exe`: the program to run
- `config.ini`: bot configuration
- `USER_GUIDE.md`: end-user instructions
- `README.md`: developer notes

## How to use

1. Put `pickbot.exe` and `config.ini` in the same folder.
2. Make sure the target game process is running:
   - `NRC-Win64-Shipping.exe`
3. Double-click `pickbot.exe`.
4. Use the hotkeys:
   - `F8`: start or stop
   - `F9`: reload `config.ini`
   - `F10`: exit

## Config

The target process is configured in `config.ini`:

```ini
[Target]
WinTitle=ahk_exe NRC-Win64-Shipping.exe
```

Keep `config.ini` next to `pickbot.exe`.

## Important notes

- Start with the game in windowed or borderless mode while testing.
- Some games ignore background window messages. In that case, this bot may not work for that game.
- Anti-cheat protected games may detect or block automation.
