from __future__ import annotations

import json
import logging
import shlex
import sys
import threading
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

import keyboard
import psutil
import pyautogui
import win32con
import win32gui
import win32process


APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"
PIC_DIR = APP_DIR / "pic"
LOG_DIR = APP_DIR / "logs"
LOG_PATH = LOG_DIR / "pickbot.log"

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

logger = logging.getLogger("pickbot")
HOTKEY_HANDLES: list[Any] = []
IMAGE_TEMPLATE_CACHE: dict[tuple[str, int, int, int, int, bool, int, int], Any] = {}

STEP_TYPE_ALIASES = {
    "click": "mouse_click",
    "mouse_click": "mouse_click",
    "hold": "mouse_hold",
    "mouse_hold": "mouse_hold",
    "drag": "mouse_drag",
    "swipe": "mouse_drag",
    "mouse_drag": "mouse_drag",
    "key": "key_tap",
    "tap": "key_tap",
    "key_tap": "key_tap",
    "wait": "wait",
    "sleep": "wait",
    "wait_pixel": "wait_until_pixel",
    "wait_until_pixel": "wait_until_pixel",
    "pixel": "wait_until_pixel",
    "wait_image": "wait_until_image",
    "wait_until_image": "wait_until_image",
    "image": "wait_until_image",
}

PARAM_ALIASES = {
    "btn": "button",
    "ms": "hold_ms",
    "hold": "hold_seconds",
    "hold_ms": "hold_ms",
    "interval": "repeat_interval_seconds",
    "repeat_interval": "repeat_interval_seconds",
    "gap": "gap_seconds",
    "wait": "gap_seconds",
    "wait_ms": "gap_ms",
    "pos": "position",
    "rel": "relative_to_window",
    "base": "base_resolution",
    "color": "rgb",
    "check": "check_interval_seconds",
    "interval_seconds": "check_interval_seconds",
    "interval_ms": "check_interval_ms",
    "file": "template",
}


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


def parse_scalar(value: str) -> Any:
    lowered = value.strip().lower()
    if lowered in {"true", "yes", "on"}:
        return True
    if lowered in {"false", "no", "off"}:
        return False

    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "on", "1"}:
            return True
        if lowered in {"false", "no", "off", "0"}:
            return False
    return bool(value)


def normalize_seconds_fields(step: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(step)

    if "hold_ms" in normalized:
        normalized["hold_seconds"] = float(normalized.pop("hold_ms")) / 1000.0
    if "gap_ms" in normalized:
        normalized["gap_seconds"] = float(normalized.pop("gap_ms")) / 1000.0
    if "check_interval_ms" in normalized:
        normalized["check_interval_seconds"] = float(normalized.pop("check_interval_ms")) / 1000.0
    if "seconds" in normalized:
        normalized["seconds"] = float(normalized["seconds"])
    if "hold_seconds" in normalized:
        normalized["hold_seconds"] = float(normalized["hold_seconds"])
    if "repeat_interval_seconds" in normalized:
        normalized["repeat_interval_seconds"] = float(normalized["repeat_interval_seconds"])
    if "gap_seconds" in normalized:
        normalized["gap_seconds"] = float(normalized["gap_seconds"])
    if "check_interval_seconds" in normalized:
        normalized["check_interval_seconds"] = float(normalized["check_interval_seconds"])

    return normalized


def parse_resolution(value: str) -> tuple[int, int]:
    cleaned = value.lower().replace("*", "x")
    parts = cleaned.split("x", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid resolution value: {value}")
    return int(parts[0]), int(parts[1])


def parse_rgb(value: str) -> tuple[int, int, int]:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 3:
        raise ValueError(f"Invalid rgb value: {value}")
    red, green, blue = (int(part) for part in parts)
    return red, green, blue


def parse_workflow_line(line: str, line_number: int) -> dict[str, Any]:
    tokens = shlex.split(line, comments=False, posix=True)
    if not tokens:
        raise ValueError(f"Line {line_number}: empty workflow line.")

    raw_type = tokens[0].lower()
    if raw_type in {"repeat", "repeat_count"}:
        if len(tokens) < 2:
            raise ValueError(f"Line {line_number}: repeat requires a count.")
        return {"type": "repeat", "count": int(parse_scalar(tokens[1]))}
    if raw_type in {"drag_down_half", "swipe_down_half"}:
        return {"type": "mouse_drag", "dy_ratio": 0.5}
    if raw_type in {"for_seconds", "repeat_for_seconds"}:
        if len(tokens) < 2:
            raise ValueError(f"Line {line_number}: for_seconds requires a duration.")
        return {"type": "for_seconds", "seconds": float(parse_scalar(tokens[1]))}
    if raw_type == "end":
        return {"type": "end"}

    step_type = STEP_TYPE_ALIASES.get(raw_type)
    if step_type is None:
        raise ValueError(f"Line {line_number}: unsupported step type '{tokens[0]}'.")

    step: dict[str, Any] = {"type": step_type}
    positional: list[str] = []

    for token in tokens[1:]:
        if "=" in token:
            key, value = token.split("=", 1)
            normalized_key = PARAM_ALIASES.get(key.lower(), key.lower())
            step[normalized_key] = parse_scalar(value)
        else:
            positional.append(token)

    if step_type == "key_tap":
        if positional:
            step["key"] = positional[0]
    elif step_type == "wait":
        if positional:
            step["seconds"] = parse_scalar(positional[0])
    elif positional:
        position = positional[0].lower()
        if position in {"cursor", "center", "window_center"}:
            step["position"] = position

    if "base_resolution" in step:
        base_width, base_height = parse_resolution(str(step["base_resolution"]))
        step["base_width"] = base_width
        step["base_height"] = base_height
        del step["base_resolution"]
    if "rgb" in step:
        step["rgb"] = parse_rgb(str(step["rgb"]))

    return normalize_seconds_fields(step)


def apply_step_defaults(step: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    step_type = str(step["type"])
    if step_type == "repeat":
        merged = dict(step)
        merged["count"] = int(merged.get("count", 0))
        merged["steps"] = list(merged.get("steps", []))
        if merged["count"] < 0:
            raise ValueError("repeat block count must be >= 0.")
        return merged
    if step_type == "for_seconds":
        merged = dict(step)
        merged["seconds"] = float(merged.get("seconds", 0.0))
        merged["steps"] = list(merged.get("steps", []))
        if merged["seconds"] < 0:
            raise ValueError("for_seconds block seconds must be >= 0.")
        return merged

    merged = deepcopy(defaults.get(step_type, {}))
    merged.update(step)
    merged["type"] = step_type
    merged = normalize_seconds_fields(merged)

    if step_type in {"mouse_click", "mouse_hold", "mouse_drag"}:
        merged.setdefault("position", "center")
        merged.setdefault("button", "left")
        merged.setdefault("repeat", 1)
        merged.setdefault("repeat_interval_seconds", 0.05)
        merged.setdefault("relative_to_window", False)
    elif step_type == "key_tap":
        merged.setdefault("hold_seconds", 0.03)
        merged.setdefault("repeat", 1)
        merged.setdefault("repeat_interval_seconds", 0.05)
    elif step_type == "wait":
        merged.setdefault("seconds", 1.0)
    elif step_type == "wait_until_pixel":
        merged.setdefault("tolerance", 10)
        merged.setdefault("check_interval_seconds", 0.2)
        merged.setdefault("relative_to_window", False)
    elif step_type == "wait_until_image":
        merged.setdefault("confidence", 0.9)
        merged.setdefault("check_interval_seconds", 0.3)
        merged.setdefault("grayscale", True)
        merged.setdefault("relative_to_window", False)

    if step_type == "mouse_hold":
        merged.setdefault("hold_seconds", 0.02)
    if step_type == "mouse_drag":
        merged.setdefault("duration_seconds", 0.5)
        merged.setdefault("steps", 20)
        merged.setdefault("dx_ratio", 0.0)
        merged.setdefault("dy_ratio", 0.5)

    if step_type == "key_tap" and not str(merged.get("key", "")).strip():
        raise ValueError("key_tap step is missing key.")

    if step_type == "wait" and float(merged.get("seconds", 0.0)) < 0:
        raise ValueError("wait step seconds must be >= 0.")
    if step_type == "wait_until_pixel":
        if "x" not in merged or "y" not in merged:
            raise ValueError("wait_until_pixel step requires x and y.")
        if "rgb" not in merged:
            raise ValueError("wait_until_pixel step requires rgb=r,g,b.")
        merged["rgb"] = tuple(int(channel) for channel in merged["rgb"])
        merged["tolerance"] = int(merged.get("tolerance", 10))
    if step_type == "wait_until_image":
        if not str(merged.get("template", "")).strip():
            raise ValueError("wait_until_image step requires template=<filename>.")
        if "x" not in merged or "y" not in merged or "w" not in merged or "h" not in merged:
            raise ValueError("wait_until_image step requires x, y, w, h.")
        merged["confidence"] = float(merged.get("confidence", 0.9))
        merged["grayscale"] = to_bool(merged.get("grayscale", True))
    if step_type == "mouse_drag":
        merged["duration_seconds"] = float(merged.get("duration_seconds", 0.5))
        merged["steps"] = max(1, int(merged.get("steps", 20)))
        merged["dx_ratio"] = float(merged.get("dx_ratio", 0.0))
        merged["dy_ratio"] = float(merged.get("dy_ratio", 0.5))
        if "dx" in merged:
            merged["dx"] = float(merged["dx"])
        if "dy" in merged:
            merged["dy"] = float(merged["dy"])

    return merged


def load_workflow(workflow_path: Path, defaults: dict[str, Any]) -> list[dict[str, Any]]:
    if not workflow_path.exists():
        raise FileNotFoundError(f"Missing workflow file next to the app: {workflow_path}")

    root_steps: list[dict[str, Any]] = []
    stack: list[dict[str, Any]] = []

    with workflow_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            step = parse_workflow_line(line, line_number)
            step_type = str(step["type"])

            if step_type == "end":
                if not stack:
                    raise ValueError(f"Line {line_number}: unexpected end without matching block.")
                completed = stack.pop()
                target_steps = root_steps if not stack else stack[-1]["steps"]
                target_steps.append(apply_step_defaults(completed, defaults))
                continue

            if step_type in {"for_seconds", "repeat"}:
                step["steps"] = []
                stack.append(step)
                continue

            normalized_step = apply_step_defaults(step, defaults)
            target_steps = root_steps if not stack else stack[-1]["steps"]
            target_steps.append(normalized_step)

    if stack:
        raise ValueError("Workflow file is missing end for a block.")

    if not root_steps:
        raise ValueError(f"Workflow file is empty: {workflow_path}")

    return root_steps


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing config.json next to the app: {CONFIG_PATH}")

    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        config = json.load(handle)

    workflow = config.setdefault("workflow", {})
    workflow_path = APP_DIR / str(workflow.get("path", "flow.txt"))
    workflow["path"] = workflow_path.name
    workflow.setdefault("default_between_seconds", 1.0)

    defaults = config.setdefault("defaults", {})
    for key in ("mouse_click", "mouse_hold", "mouse_drag", "key_tap", "wait"):
        defaults.setdefault(key, {})
    defaults.setdefault("wait_until_pixel", {})
    defaults.setdefault("wait_until_image", {})

    config["workflow_path"] = str(workflow_path)
    config["steps"] = load_workflow(workflow_path, defaults)
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
    if "x" in step and "y" in step:
        x = int(step["x"])
        y = int(step["y"])
        if "base_width" in step and "base_height" in step:
            screen_width, screen_height = pyautogui.size()
            x = round(x * screen_width / int(step["base_width"]))
            y = round(y * screen_height / int(step["base_height"]))
        if to_bool(step.get("relative_to_window", False)):
            left, top, _, _ = window_rect(hwnd)
            x += left
            y += top
        return x, y

    position = str(step.get("position", "center")).lower()
    if position == "cursor":
        return current_mouse_position()
    if position == "window_center":
        left, top, right, bottom = window_rect(hwnd)
        return int((left + right) / 2), int((top + bottom) / 2)

    width, height = pyautogui.size()
    return int(width / 2), int(height / 2)


def resolve_screen_point(hwnd: int, step: dict[str, Any]) -> tuple[int, int]:
    x = int(step["x"])
    y = int(step["y"])
    if "base_width" in step and "base_height" in step:
        screen_width, screen_height = pyautogui.size()
        x = round(x * screen_width / int(step["base_width"]))
        y = round(y * screen_height / int(step["base_height"]))
    if to_bool(step.get("relative_to_window", False)):
        left, top, _, _ = window_rect(hwnd)
        x += left
        y += top
    return x, y


def resolve_screen_rect(hwnd: int, step: dict[str, Any]) -> tuple[int, int, int, int]:
    x, y = resolve_screen_point(hwnd, step)
    width = int(step["w"])
    height = int(step["h"])
    if "base_width" in step and "base_height" in step:
        screen_width, screen_height = pyautogui.size()
        width = round(width * screen_width / int(step["base_width"]))
        height = round(height * screen_height / int(step["base_height"]))
    return x, y, width, height


def scale_delta(step: dict[str, Any], dx: float, dy: float) -> tuple[float, float]:
    if "base_width" in step and "base_height" in step:
        screen_width, screen_height = pyautogui.size()
        dx = dx * screen_width / int(step["base_width"])
        dy = dy * screen_height / int(step["base_height"])
    return dx, dy


def load_reference_template(step: dict[str, Any]) -> Any:
    import cv2  # type: ignore
    import numpy as np  # type: ignore

    template_path = PIC_DIR / str(step["template"])
    if not template_path.exists():
        raise FileNotFoundError(f"Missing template image: {template_path}")

    grayscale = to_bool(step.get("grayscale", True))
    x = int(step["x"])
    y = int(step["y"])
    width = int(step["w"])
    height = int(step["h"])
    base_width = int(step.get("base_width", 0))
    base_height = int(step.get("base_height", 0))
    cache_key = (str(template_path), x, y, width, height, grayscale, base_width, base_height)
    if cache_key in IMAGE_TEMPLATE_CACHE:
        return IMAGE_TEMPLATE_CACHE[cache_key]

    image_bytes = template_path.read_bytes()
    image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Failed to load template image: {template_path}")

    cropped = image[y : y + height, x : x + width]
    if cropped.size == 0:
        raise ValueError(f"Template crop is empty: {template_path}")
    if grayscale:
        cropped = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)

    IMAGE_TEMPLATE_CACHE[cache_key] = cropped
    return cropped


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


def perform_wait(step: dict[str, Any], stop_event: threading.Event, bot: "Bot") -> None:
    seconds = float(step.get("seconds", 0.0))
    logger.info("Wait: %.3fs", seconds)
    interruptible_sleep(stop_event, seconds, bot)


def color_matches(actual: tuple[int, int, int], expected: tuple[int, int, int], tolerance: int) -> bool:
    return all(abs(int(actual[index]) - int(expected[index])) <= tolerance for index in range(3))


def perform_wait_until_pixel(hwnd: int, step: dict[str, Any], stop_event: threading.Event, bot: "Bot") -> None:
    x, y = resolve_screen_point(hwnd, step)
    expected = tuple(int(channel) for channel in step["rgb"])
    tolerance = int(step.get("tolerance", 10))
    check_interval_seconds = float(step.get("check_interval_seconds", 0.2))

    logger.info("Wait-until-pixel: %s,%s -> %s tolerance=%d", x, y, expected, tolerance)
    while not stop_event.is_set():
        if bot.check_safety_stop():
            return
        actual = tuple(int(channel) for channel in pyautogui.pixel(x, y))
        if color_matches(actual, expected, tolerance):
            logger.info("Pixel matched at %s,%s: %s", x, y, actual)
            return
        interruptible_sleep(stop_event, check_interval_seconds, bot)


def perform_wait_until_image(hwnd: int, step: dict[str, Any], stop_event: threading.Event, bot: "Bot") -> None:
    import cv2  # type: ignore
    import numpy as np  # type: ignore
    from PIL import ImageGrab  # type: ignore

    left, top, width, height = resolve_screen_rect(hwnd, step)
    confidence = float(step.get("confidence", 0.9))
    grayscale = to_bool(step.get("grayscale", True))
    check_interval_seconds = float(step.get("check_interval_seconds", 0.3))
    template = load_reference_template(step)

    logger.info(
        "Wait-until-image: %s region=%s,%s,%s,%s confidence=%.3f",
        step["template"],
        left,
        top,
        width,
        height,
        confidence,
    )
    while not stop_event.is_set():
        if bot.check_safety_stop():
            return

        screenshot = ImageGrab.grab(bbox=(left, top, left + width, top + height))
        frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        if grayscale:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if frame.shape[:2] != template.shape[:2]:
            frame = cv2.resize(frame, (template.shape[1], template.shape[0]))

        score = float(cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)[0][0])
        if score >= confidence:
            logger.info("Image matched: %s score=%.4f", step["template"], score)
            return

        interruptible_sleep(stop_event, check_interval_seconds, bot)


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


def perform_mouse_drag(hwnd: int, step: dict[str, Any], stop_event: threading.Event, bot: "Bot") -> None:
    button = str(step.get("button", "left"))
    repeat = int(step.get("repeat", 1))
    repeat_interval_seconds = float(step.get("repeat_interval_seconds", 0.05))
    duration_seconds = float(step.get("duration_seconds", 0.5))
    move_steps = max(1, int(step.get("steps", 20)))
    start_x, start_y = resolve_click_point(hwnd, step)

    screen_width, screen_height = pyautogui.size()
    dx = float(step.get("dx", 0.0))
    dy = float(step.get("dy", 0.0))
    dx, dy = scale_delta(step, dx, dy)
    dx += float(step.get("dx_ratio", 0.0)) * screen_width
    dy += float(step.get("dy_ratio", 0.0)) * screen_height
    end_x = round(start_x + dx)
    end_y = round(start_y + dy)

    for index in range(repeat):
        if str(step.get("position", "")).lower() != "cursor":
            pyautogui.moveTo(start_x, start_y)
        pyautogui.mouseDown(x=start_x, y=start_y, button=button)
        drag_started = time.monotonic()
        tick_seconds = max(0.005, duration_seconds / move_steps)
        while True:
            if bot.check_safety_stop() or stop_event.is_set():
                pyautogui.mouseUp(button=button)
                return

            elapsed = min(duration_seconds, time.monotonic() - drag_started)
            progress = 1.0 if duration_seconds <= 0 else elapsed / duration_seconds
            current_x = round(start_x + dx * progress)
            current_y = round(start_y + dy * progress)
            pyautogui.moveTo(current_x, current_y)

            if progress >= 1.0:
                break

            interruptible_sleep(stop_event, tick_seconds, bot)

        pyautogui.mouseUp(x=end_x, y=end_y, button=button)
        if index + 1 < repeat:
            interruptible_sleep(stop_event, repeat_interval_seconds, bot)

    logger.info(
        "Mouse drag: %s from %s,%s to %s,%s x%d (duration %.3fs)",
        button,
        start_x,
        start_y,
        end_x,
        end_y,
        repeat,
        duration_seconds,
    )


def execute_step(hwnd: int, step: dict[str, Any], stop_event: threading.Event, bot: "Bot") -> None:
    step_type = str(step["type"]).lower()

    if step_type == "wait":
        perform_wait(step, stop_event, bot)
    elif step_type == "wait_until_pixel":
        perform_wait_until_pixel(hwnd, step, stop_event, bot)
    elif step_type == "wait_until_image":
        perform_wait_until_image(hwnd, step, stop_event, bot)
    elif step_type == "key_tap":
        perform_key_tap(step, stop_event, bot)
    elif step_type == "mouse_click":
        perform_mouse_click(hwnd, step, stop_event, bot)
    elif step_type == "mouse_hold":
        perform_mouse_hold(hwnd, step, stop_event, bot)
    elif step_type == "mouse_drag":
        perform_mouse_drag(hwnd, step, stop_event, bot)
    else:
        raise ValueError(f"Unsupported step type: {step_type}")


def execute_plan(hwnd: int, steps: list[dict[str, Any]], stop_event: threading.Event, bot: "Bot", default_between: float) -> bool:
    for index, step in enumerate(steps):
        if bot.check_safety_stop() or stop_event.is_set():
            return False

        step_type = str(step["type"]).lower()
        if step_type == "repeat":
            count = int(step.get("count", 0))
            logger.info("Repeat block started: %d", count)
            for _ in range(count):
                if bot.check_safety_stop() or stop_event.is_set():
                    return False
                if not execute_plan(hwnd, list(step.get("steps", [])), stop_event, bot, default_between):
                    return False
            logger.info("Repeat block completed: %d", count)
        elif step_type == "for_seconds":
            seconds = float(step.get("seconds", 0.0))
            deadline = time.monotonic() + max(0.0, seconds)
            logger.info("For-seconds block started: %.3fs", seconds)
            while time.monotonic() < deadline:
                remaining = deadline - time.monotonic()
                if bot.check_safety_stop() or stop_event.is_set():
                    return False
                if not execute_plan(hwnd, list(step.get("steps", [])), stop_event, bot, default_between):
                    return False
                if remaining <= 0:
                    break
            logger.info("For-seconds block completed: %.3fs", seconds)
        else:
            execute_step(hwnd, step, stop_event, bot)

        if bot.check_safety_stop() or stop_event.is_set():
            return False

        if index + 1 < len(steps):
            gap_seconds = float(step.get("gap_seconds", default_between))
            if gap_seconds > 0:
                interruptible_sleep(stop_event, gap_seconds, bot)

    return True


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
        if not to_bool(safety.get("mouse_corner_stop", True)):
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

            if to_bool(target.get("bring_to_front", True)):
                try:
                    activate_window(hwnd)
                except Exception as exc:
                    logger.warning("Failed to activate target window: %s", exc)

            try:
                steps = config["steps"]
                default_between = float(config.get("workflow", {}).get("default_between_seconds", 1.0))
                if execute_plan(hwnd, steps, self.stop_event, self, default_between):
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
    logger.info("Workflow path: %s", bot.config.get("workflow_path", APP_DIR / "flow.txt"))
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
