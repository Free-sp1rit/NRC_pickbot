from __future__ import annotations

import json
import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any

import keyboard
import pyautogui
import psutil
import win32con
import win32gui
import win32process


APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"
LOG_DIR = APP_DIR / "logs"
LOG_PATH = LOG_DIR / "pickbot.log"

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

logger = logging.getLogger("pickbot")
HOTKEY_HANDLES: list[Any] = []


def configure_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(message)s", "%Y-%m-%d %H:%M:%S")

    file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)


def current_mouse_position() -> tuple[int, int]:
    pos = pyautogui.position()
    return int(pos.x), int(pos.y)


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing config.json next to the app: {CONFIG_PATH}")

    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        config = json.load(handle)

    steps = config.get("steps", [])
    if not isinstance(steps, list) or not steps:
        raise ValueError("config.json must contain a non-empty steps array.")

    return config


def find_target_window(process_name: str, title_contains: str) -> int:
    process_name = process_name.lower().strip()
    title_contains = title_contains.lower().strip()
    matches: list[int] = []

    def callback(hwnd: int, _: Any) -> bool:
        try:
            if not win32gui.IsWindowVisible(hwnd):
                return True

            title = win32gui.GetWindowText(hwnd)
            if title_contains and title_contains not in title.lower():
                return True

            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            if process_name and proc.name().lower() != process_name:
                return True

            matches.append(hwnd)
            return False
        except Exception:
            return True

    try:
        win32gui.EnumWindows(callback, None)
    except Exception as exc:
        logger.warning("EnumWindows failed while searching for target window: %s", exc)
    return matches[0] if matches else 0


def activate_window(hwnd: int) -> None:
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.08)


def window_rect(hwnd: int) -> tuple[int, int, int, int]:
    return win32gui.GetWindowRect(hwnd)


def resolve_click_point(hwnd: int, step: dict[str, Any]) -> tuple[int, int]:
    if str(step.get("position", "")).lower() == "cursor":
        return current_mouse_position()

    x = int(step["x"])
    y = int(step["y"])
    if bool(step.get("relative_to_window", True)):
        left, top, _, _ = window_rect(hwnd)
        x += left
        y += top
    return x, y


def interruptible_sleep(stop_event: threading.Event | None, seconds: float, bot: "Bot | None" = None) -> None:
    deadline = time.monotonic() + max(0.0, seconds)
    while time.monotonic() < deadline:
        if stop_event is not None and stop_event.is_set():
            return
        if bot is not None and bot.check_safety_stop():
            return
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        time.sleep(min(0.05, remaining))


def perform_key_tap(step: dict[str, Any], stop_event: threading.Event, bot: "Bot") -> None:
    key = str(step["key"])
    hold_seconds = float(step.get("hold_seconds", 0.03))
    repeat = int(step.get("repeat", 1))
    repeat_interval_seconds = float(step.get("repeat_interval_seconds", 0.05))

    for index in range(repeat):
        pyautogui.keyDown(key)
        interruptible_sleep(stop_event, hold_seconds, bot)
        pyautogui.keyUp(key)
        if index + 1 < repeat:
            interruptible_sleep(stop_event, repeat_interval_seconds, bot)

    logger.info("Key tap: %s x%d (hold %.3fs)", key, repeat, hold_seconds)


def perform_mouse_click(hwnd: int, step: dict[str, Any], stop_event: threading.Event, bot: "Bot") -> None:
    button = str(step.get("button", "left"))
    repeat = int(step.get("repeat", 1))
    repeat_interval_seconds = float(step.get("repeat_interval_seconds", 0.05))
    x, y = resolve_click_point(hwnd, step)

    for index in range(repeat):
        if str(step.get("position", "")).lower() != "cursor":
            pyautogui.moveTo(x, y)
        pyautogui.click(x=x, y=y, button=button)
        if index + 1 < repeat:
            interruptible_sleep(stop_event, repeat_interval_seconds, bot)

    logger.info("Mouse click: %s at %s,%s x%d", button, x, y, repeat)


def perform_mouse_hold(hwnd: int, step: dict[str, Any], stop_event: threading.Event, bot: "Bot") -> None:
    button = str(step.get("button", "left"))
    hold_seconds = float(step.get("hold_seconds", 0.02))
    repeat = int(step.get("repeat", 1))
    repeat_interval_seconds = float(step.get("repeat_interval_seconds", 0.05))
    x, y = resolve_click_point(hwnd, step)

    for index in range(repeat):
        if str(step.get("position", "")).lower() != "cursor":
            pyautogui.moveTo(x, y)
        pyautogui.mouseDown(x=x, y=y, button=button)
        interruptible_sleep(stop_event, hold_seconds, bot)
        pyautogui.mouseUp(x=x, y=y, button=button)
        if index + 1 < repeat:
            interruptible_sleep(stop_event, repeat_interval_seconds, bot)

    logger.info("Mouse hold: %s at %s,%s x%d (hold %.3fs)", button, x, y, repeat, hold_seconds)


def execute_step(hwnd: int, step: dict[str, Any], stop_event: threading.Event, bot: "Bot") -> None:
    step_type = str(step["type"]).lower()

    if step_type == "key_tap":
        perform_key_tap(step, stop_event, bot)
    elif step_type == "mouse_click":
        perform_mouse_click(hwnd, step, stop_event, bot)
    elif step_type == "mouse_hold":
        perform_mouse_hold(hwnd, step, stop_event, bot)
    else:
        raise ValueError(f"Unsupported step type: {step_type}")

    after_seconds = float(step.get("after_seconds", 0.0))
    if after_seconds > 0:
        interruptible_sleep(stop_event, after_seconds, bot)


class Bot:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.running = False
        self.config = load_config()

    def reload_config(self) -> None:
        with self.lock:
            self.config = load_config()
            bind_hotkeys(self)
        logger.info("Config reloaded.")

    def toggle(self) -> None:
        with self.lock:
            self.running = not self.running
            state = "started" if self.running else "stopped"
        logger.info("Bot %s.", state)

    def stop(self) -> None:
        self.stop_event.set()
        logger.info("Bot exit requested.")

    def emergency_stop(self, reason: str) -> None:
        with self.lock:
            was_running = self.running
            self.running = False
        if was_running:
            logger.warning("Emergency stop triggered: %s", reason)

    def check_safety_stop(self) -> bool:
        safety = self.config.get("safety", {})
        if not bool(safety.get("mouse_corner_stop", True)):
            return False

        corner_size = int(safety.get("corner_size", 5))
        mouse_x, mouse_y = current_mouse_position()
        if mouse_x <= corner_size and mouse_y <= corner_size:
            self.emergency_stop("mouse moved to top-left corner")
            return True
        return False

    def worker(self) -> None:
        while not self.stop_event.is_set():
            with self.lock:
                config = self.config
                running = self.running

            if not running:
                idle_poll = float(config.get("runtime", {}).get("idle_poll_seconds", 0.2))
                interruptible_sleep(self.stop_event, idle_poll)
                continue

            if self.check_safety_stop():
                interruptible_sleep(self.stop_event, 0.2)
                continue

            cycle_started = time.monotonic()
            target = config.get("target", {})
            hwnd = find_target_window(
                str(target.get("process_name", "")),
                str(target.get("window_title_contains", "")),
            )

            if not hwnd:
                logger.info("Target window not found.")
                interruptible_sleep(self.stop_event, 0.5)
                continue

            if bool(target.get("bring_to_front", True)):
                try:
                    activate_window(hwnd)
                except Exception as exc:
                    logger.warning("Failed to activate target window: %s", exc)

            try:
                for step in config["steps"]:
                    if self.check_safety_stop() or self.stop_event.is_set():
                        break
                    execute_step(hwnd, step, self.stop_event, self)
                else:
                    logger.info("Cycle completed.")
            except Exception as exc:
                logger.exception("Cycle failed: %s", exc)

            cycle_delay = float(config.get("runtime", {}).get("cycle_delay_seconds", 0.0))
            elapsed = time.monotonic() - cycle_started
            if elapsed < cycle_delay:
                interruptible_sleep(self.stop_event, cycle_delay - elapsed, self)


def bind_hotkeys(bot: Bot) -> None:
    global HOTKEY_HANDLES

    for handle in HOTKEY_HANDLES:
        try:
            keyboard.remove_hotkey(handle)
        except (KeyError, ValueError):
            pass
    HOTKEY_HANDLES = []

    hotkeys = bot.config.get("hotkeys", {})
    HOTKEY_HANDLES.append(keyboard.add_hotkey(str(hotkeys.get("toggle", "f8")), bot.toggle))
    HOTKEY_HANDLES.append(keyboard.add_hotkey(str(hotkeys.get("reload", "f9")), bot.reload_config))
    HOTKEY_HANDLES.append(keyboard.add_hotkey(str(hotkeys.get("exit", "f10")), bot.stop))


def main() -> None:
    configure_logging()
    bot = Bot()
    bind_hotkeys(bot)

    logger.info("Pickbot ready.")
    logger.info("App dir: %s", APP_DIR)
    logger.info("Config path: %s", CONFIG_PATH)
    logger.info(
        "Hotkeys: toggle=%s reload=%s exit=%s",
        bot.config.get("hotkeys", {}).get("toggle", "f8"),
        bot.config.get("hotkeys", {}).get("reload", "f9"),
        bot.config.get("hotkeys", {}).get("exit", "f10"),
    )

    worker_thread = threading.Thread(target=bot.worker, daemon=True)
    worker_thread.start()

    try:
        while not bot.stop_event.is_set():
            time.sleep(0.2)
    except KeyboardInterrupt:
        bot.stop()


if __name__ == "__main__":
    main()
