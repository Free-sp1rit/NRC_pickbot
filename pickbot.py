from __future__ import annotations

import json
import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any

import cv2
import keyboard
import mss
import numpy as np
import pyautogui
import psutil
import pydirectinput
import win32con
import win32gui
import win32process


APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
PROJECT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"
LOG_DIR = APP_DIR / "logs"
LOG_PATH = LOG_DIR / "pickbot.log"

pydirectinput.FAILSAFE = False
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


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing config.json next to the app: {CONFIG_PATH}")

    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        config = json.load(handle)

    if not config.get("steps"):
        raise ValueError("config.json must contain at least one step.")

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
    time.sleep(0.1)


def window_rect(hwnd: int) -> tuple[int, int, int, int]:
    return win32gui.GetWindowRect(hwnd)


def resolve_region(hwnd: int, region: list[int], relative_to_window: bool = True) -> dict[str, int]:
    if len(region) != 4:
        raise ValueError("Region must be [x, y, width, height].")

    x, y, width, height = region
    if relative_to_window:
        left, top, _, _ = window_rect(hwnd)
        x += left
        y += top

    return {"left": x, "top": y, "width": width, "height": height}


def capture_region(region: dict[str, int]) -> np.ndarray:
    return capture_region_with_backend(region, "mss")


def capture_region_with_backend(region: dict[str, int], backend: str) -> np.ndarray:
    if backend == "pyautogui":
        pil = pyautogui.screenshot(
            region=(region["left"], region["top"], region["width"], region["height"])
        )
        return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

    with mss.mss() as sct:
        frame = np.array(sct.grab(region))
    return frame[:, :, :3]


def match_template(hwnd: int, step: dict[str, Any]) -> tuple[float, tuple[int, int]]:
    template_path = APP_DIR / step["template"]
    if not template_path.exists():
        template_path = PROJECT_DIR / step["template"]
    template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
    if template is None:
        raise FileNotFoundError(f"Template not found or unreadable: {template_path}")

    region = resolve_region(
        hwnd,
        step["region"],
        bool(step.get("relative_to_window", True)),
    )
    frame = capture_region_with_backend(region, str(step.get("capture_backend", "pyautogui")))
    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    if frame_gray.shape[0] < template.shape[0] or frame_gray.shape[1] < template.shape[1]:
        raise ValueError(f"Template is larger than capture region: {template_path}")

    result = cv2.matchTemplate(frame_gray, template, cv2.TM_CCOEFF_NORMED)
    _, max_value, _, max_location = cv2.minMaxLoc(result)
    return float(max_value), max_location


def press_key(step: dict[str, Any], config: dict[str, Any]) -> None:
    key = step["key"]
    press_seconds = float(step.get("press_seconds", 0.05))
    count = int(step.get("count", 1))
    gap_seconds = float(step.get("gap_seconds", 0.05))
    backend = str(config.get("input", {}).get("backend", "pyautogui")).lower()

    for index in range(count):
        if backend == "pyautogui":
            pyautogui.keyDown(key)
            time.sleep(press_seconds)
            pyautogui.keyUp(key)
        else:
            pydirectinput.keyDown(key)
            time.sleep(press_seconds)
            pydirectinput.keyUp(key)
        if index + 1 < count:
            time.sleep(gap_seconds)

    logger.info("Pressed key: %s via %s", key, backend)


def click_mouse(hwnd: int, config: dict[str, Any], step: dict[str, Any]) -> None:
    region = resolve_region(
        hwnd,
        [int(step["x"]), int(step["y"]), 1, 1],
        bool(step.get("relative_to_window", True)),
    )
    button = str(step.get("button", "left"))
    backend = str(config.get("input", {}).get("backend", "pyautogui")).lower()

    if backend == "pyautogui":
        pyautogui.moveTo(region["left"], region["top"])
        pyautogui.click(button=button)
    else:
        pydirectinput.click(region["left"], region["top"], button=button)
    logger.info("Clicked %s at %s,%s via %s", button, region["left"], region["top"], backend)


def wait_for_image(hwnd: int, config: dict[str, Any], step: dict[str, Any]) -> None:
    timeout_seconds = float(step.get("timeout_seconds", 5.0))
    threshold = float(step.get("threshold", 0.92))
    poll_seconds = float(config.get("matching", {}).get("default_poll_seconds", 0.2))
    optional = bool(step.get("optional", False))
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        score, _ = match_template(hwnd, step)
        if score >= threshold:
            logger.info("Template matched: %s (%.3f)", step["template"], score)
            return
        time.sleep(poll_seconds)

    if optional:
        logger.info("Optional template not matched: %s", step["template"])
        return

    raise TimeoutError(f"Template not matched in time: {step['template']}")


def execute_step(hwnd: int, config: dict[str, Any], step: dict[str, Any]) -> None:
    step_type = step["type"]

    if step_type == "key":
        press_key(step, config)
    elif step_type == "click":
        click_mouse(hwnd, config, step)
    elif step_type == "sleep":
        duration = float(step.get("seconds", 1.0))
        time.sleep(duration)
        logger.info("Slept for %.2f seconds", duration)
    elif step_type == "wait_image":
        wait_for_image(hwnd, config, step)
    else:
        raise ValueError(f"Unsupported step type: {step_type}")


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

    def worker(self) -> None:
        while not self.stop_event.is_set():
            with self.lock:
                config = self.config
                running = self.running

            if not running:
                time.sleep(0.1)
                continue

            cycle_started = time.monotonic()
            target = config["target"]
            try:
                hwnd = find_target_window(
                    str(target.get("process_name", "")),
                    str(target.get("window_title_contains", "")),
                )
            except Exception as exc:
                logger.exception("Target discovery failed: %s", exc)
                time.sleep(0.5)
                continue

            if not hwnd:
                logger.info("Target window not found.")
                time.sleep(0.5)
                continue

            if bool(target.get("bring_to_front", True)):
                try:
                    activate_window(hwnd)
                except Exception as exc:  # pragma: no cover - Windows focus issues are environment-specific
                    logger.warning("Failed to activate target window: %s", exc)

            try:
                for step in config["steps"]:
                    execute_step(hwnd, config, step)
                logger.info("Cycle completed.")
            except Exception as exc:
                logger.exception("Cycle failed: %s", exc)

            interval = float(config.get("loop", {}).get("interval_seconds", 1.0))
            elapsed = time.monotonic() - cycle_started
            if elapsed < interval:
                time.sleep(interval - elapsed)


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

    logger.info("Python pickbot ready.")
    logger.info("App dir: %s", APP_DIR)
    logger.info("Config path: %s", CONFIG_PATH)
    logger.info("Hotkeys: toggle=%s reload=%s exit=%s",
                bot.config.get("hotkeys", {}).get("toggle", "f8"),
                bot.config.get("hotkeys", {}).get("reload", "f9"),
                bot.config.get("hotkeys", {}).get("exit", "f10"))

    worker_thread = threading.Thread(target=bot.worker, daemon=True)
    worker_thread.start()

    try:
        while not bot.stop_event.is_set():
            time.sleep(0.2)
    except KeyboardInterrupt:
        bot.stop()


if __name__ == "__main__":
    main()
