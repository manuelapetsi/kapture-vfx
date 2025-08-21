from fastapi import WebSocket, WebSocketDisconnect
from .services.processor import FrameProcessor
import re
import time
from typing import Dict

processor = FrameProcessor()

# Rate limiting per connection
connection_limits: Dict[str, Dict[str, float]] = {}

def validate_hex_color(hex_color: str) -> bool:
	"""Validate hex color format"""
	pattern = r'^#[0-9A-Fa-f]{6}$'
	return bool(re.match(pattern, hex_color))

def validate_numeric_param(value, min_val: float, max_val: float, default: float) -> float:
	"""Safely convert and validate numeric parameters"""
	if value is None:
		return default
	try:
		num = float(value)
		return max(min_val, min(max_val, num))
	except (ValueError, TypeError):
		return default

def check_rate_limit(client_id: str, max_requests: int = 30, window: int = 1) -> bool:
	"""Simple rate limiting check"""
	now = time.time()
	if client_id not in connection_limits:
		connection_limits[client_id] = {"count": 0, "window_start": now}
	
	limit_data = connection_limits[client_id]
	
	if now - limit_data["window_start"] > window:
		limit_data["count"] = 0
		limit_data["window_start"] = now
	
	if limit_data["count"] >= max_requests:
		return False
	
	limit_data["count"] += 1
	return True

async def handle_ws(websocket: WebSocket):
	await websocket.accept()
	client_id = f"{websocket.client.host}:{websocket.client.port}"
	
	try:
		while True:
			message = await websocket.receive_json()
			
			# Rate limiting check
			if not check_rate_limit(client_id):
				await websocket.send_json({"type": "error", "message": "rate_limit_exceeded"})
				continue
			
			kind = message.get("type")
			
			if kind == "frame":
				img_data = message.get("data")
				if not img_data or not isinstance(img_data, str):
					await websocket.send_json({"type": "error", "message": "invalid_frame_data"})
					continue
				
				# Check base64 data size (roughly 10MB limit)
				if len(img_data) > 14000000:
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
				processor.background_ready = False
				await websocket.send_json({"type": "toast", "message": "Background cleared"})
				await websocket.send_json({"type": "ok"})
				
			elif kind == "set_color":
				hex_color = message.get("hex", "#ff0000")
				if not validate_hex_color(hex_color):
					await websocket.send_json({"type": "error", "message": "invalid_hex_color"})
					continue
				
				tol = int(validate_numeric_param(message.get("tolerance"), 1, 90, 10))
				s_min = int(validate_numeric_param(message.get("s_min"), 0, 255, 120))
				v_min = int(validate_numeric_param(message.get("v_min"), 0, 255, 70))
				
				processor.set_color_hex(hex_color, tolerance_h=tol, s_min=s_min, v_min=v_min)
				await websocket.send_json({"type": "ok"})
				
			elif kind == "set_params":
				# Validate all parameters with safe bounds
				blur_ksize = validate_numeric_param(message.get("blur_ksize"), 3, 15, None)
				morph_iterations = validate_numeric_param(message.get("morph_iterations"), 1, 10, None)
				morph_kernel_size = validate_numeric_param(message.get("morph_kernel_size"), 3, 15, None)
				min_area_ratio = validate_numeric_param(message.get("min_area_ratio"), 0.0, 1.0, None)
				
				# Ensure odd values for kernel sizes
				if blur_ksize is not None and int(blur_ksize) % 2 == 0:
					blur_ksize = int(blur_ksize) + 1
				if morph_kernel_size is not None and int(morph_kernel_size) % 2 == 0:
					morph_kernel_size = int(morph_kernel_size) + 1
				
				processor.set_params(
					blur_ksize=int(blur_ksize) if blur_ksize is not None else None,
					morph_iterations=int(morph_iterations) if morph_iterations is not None else None,
					morph_kernel_size=int(morph_kernel_size) if morph_kernel_size is not None else None,
					preview_mask=message.get("preview_mask"),
					keep_largest=message.get("keep_largest"),
					min_area_ratio=min_area_ratio,
					skin_protect=message.get("skin_protect"),
				)
				await websocket.send_json({"type": "ok"})
			else:
				await websocket.send_json({"type": "error", "message": "unknown_message_type"})
				
	except WebSocketDisconnect:
		# Clean up rate limiting data
		if client_id in connection_limits:
			del connection_limits[client_id]
		return
	except Exception as e:
		await websocket.send_json({"type": "error", "message": "internal_error"})
		if client_id in connection_limits:
			del connection_limits[client_id]
		return
