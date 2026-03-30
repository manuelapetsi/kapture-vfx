import json
import os
import re
import time
from collections import deque
from typing import Any, Deque, Optional

from fastapi import WebSocket, WebSocketDisconnect

from .security import get_allowed_origins, is_allowed_websocket_origin
from .services.processor import FrameProcessor


HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
ALLOWED_WS_ORIGINS = set(get_allowed_origins())


def _get_int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


MAX_REQUESTS_PER_SECOND = _get_int_env("MAX_REQUESTS_PER_SECOND", 20, 1, 60)
MAX_WS_MESSAGE_BYTES = _get_int_env("MAX_WS_MESSAGE_BYTES", 4_000_000, 4_096, 20_000_000)
MAX_FRAME_DATA_CHARS = max(1_024, MAX_WS_MESSAGE_BYTES - 1_024)


class ConnectionRateLimiter:
    def __init__(self, max_requests: int = MAX_REQUESTS_PER_SECOND, window_seconds: float = 1.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.events: Deque[float] = deque()

    def allow(self) -> bool:
        now = time.monotonic()
        while self.events and now - self.events[0] >= self.window_seconds:
            self.events.popleft()

        if len(self.events) >= self.max_requests:
            return False

        self.events.append(now)
        return True

def validate_hex_color(hex_color: str) -> bool:
    return bool(HEX_COLOR_PATTERN.match(hex_color))


def validate_numeric_param(
    value: Any,
    min_val: float,
    max_val: float,
    default: Optional[float],
) -> Optional[float]:
    if value is None:
        return default
    try:
        num = float(value)
        return max(min_val, min(max_val, num))
    except (ValueError, TypeError):
        return default


def validate_bool_param(value: Any, default: Optional[bool] = None) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


async def handle_ws(websocket: WebSocket):
    if not is_allowed_websocket_origin(
        origin=websocket.headers.get("origin"),
        host=websocket.headers.get("host"),
        allowed_origins=ALLOWED_WS_ORIGINS,
    ):
        await websocket.close(code=1008)
        return

    await websocket.accept()
    processor = FrameProcessor()
    rate_limiter = ConnectionRateLimiter()

    try:
        while True:
            raw_message = await websocket.receive_text()
            if len(raw_message) > MAX_WS_MESSAGE_BYTES:
                await websocket.send_json({"type": "error", "message": "message_too_large"})
                continue

            try:
                message = json.loads(raw_message)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "invalid_json"})
                continue

            if not isinstance(message, dict):
                await websocket.send_json({"type": "error", "message": "invalid_message"})
                continue

            kind = message.get("type")
            if not isinstance(kind, str):
                await websocket.send_json({"type": "error", "message": "unknown_message_type"})
                continue

            if kind == "frame":
                if not rate_limiter.allow():
                    await websocket.send_json({"type": "error", "message": "rate_limit_exceeded"})
                    continue

                img_data = message.get("data")
                if not img_data or not isinstance(img_data, str):
                    await websocket.send_json({"type": "error", "message": "invalid_frame_data"})
                    continue

                if len(img_data) > MAX_FRAME_DATA_CHARS:
                    await websocket.send_json({"type": "error", "message": "frame_too_large"})
                    continue

                frame = FrameProcessor.decode_base64_image(img_data)
                if frame is None:
                    await websocket.send_json({"type": "error", "message": "bad_frame"})
                    continue

                processed = processor.process_frame(frame)
                if processor.pop_just_captured():
                    await websocket.send_json({"type": "toast", "message": "Background captured"})
                out_data = FrameProcessor.encode_base64_image(processed)
                await websocket.send_json({"type": "frame", "data": out_data})

            elif kind == "reset_background":
                processor.clear_background()
                await websocket.send_json({"type": "toast", "message": "Background cleared"})
                await websocket.send_json({"type": "ok"})

            elif kind == "set_color":
                hex_color = message.get("hex", "#ff0000")
                if not isinstance(hex_color, str) or not validate_hex_color(hex_color):
                    await websocket.send_json({"type": "error", "message": "invalid_hex_color"})
                    continue

                tol = int(validate_numeric_param(message.get("tolerance"), 1, 90, 10))
                s_min = int(validate_numeric_param(message.get("s_min"), 0, 255, 120))
                v_min = int(validate_numeric_param(message.get("v_min"), 0, 255, 70))

                processor.set_color_hex(hex_color, tolerance_h=tol, s_min=s_min, v_min=v_min)
                await websocket.send_json({"type": "toast", "message": "Target color updated"})
                await websocket.send_json({"type": "ok"})

            elif kind == "set_params":
                blur_ksize = validate_numeric_param(message.get("blur_ksize"), 3, 15, None)
                morph_iterations = validate_numeric_param(message.get("morph_iterations"), 1, 10, None)
                morph_kernel_size = validate_numeric_param(message.get("morph_kernel_size"), 3, 15, None)
                min_area_ratio = validate_numeric_param(message.get("min_area_ratio"), 0.0, 1.0, None)

                if blur_ksize is not None and int(blur_ksize) % 2 == 0:
                    blur_ksize = int(blur_ksize) + 1
                if morph_kernel_size is not None and int(morph_kernel_size) % 2 == 0:
                    morph_kernel_size = int(morph_kernel_size) + 1

                processor.set_params(
                    blur_ksize=int(blur_ksize) if blur_ksize is not None else None,
                    morph_iterations=int(morph_iterations) if morph_iterations is not None else None,
                    morph_kernel_size=int(morph_kernel_size) if morph_kernel_size is not None else None,
                    preview_mask=validate_bool_param(message.get("preview_mask")),
                    keep_largest=validate_bool_param(message.get("keep_largest")),
                    min_area_ratio=min_area_ratio,
                    skin_protect=validate_bool_param(message.get("skin_protect")),
                )
                await websocket.send_json({"type": "ok"})
            else:
                await websocket.send_json({"type": "error", "message": "unknown_message_type"})

    except WebSocketDisconnect:
        return
    except Exception:
        try:
            await websocket.send_json({"type": "error", "message": "internal_error"})
        except Exception:
            pass
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
