from fastapi import WebSocket, WebSocketDisconnect
from .services.processor import FrameProcessor

processor = FrameProcessor()

async def handle_ws(websocket: WebSocket):
	await websocket.accept()
	try:
		while True:
			message = await websocket.receive_json()
			kind = message.get("type")
			if kind == "frame":
				img_data = message.get("data")
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
				tol = int(message.get("tolerance", 10))
				s_min = int(message.get("s_min", 120))
				v_min = int(message.get("v_min", 70))
				processor.set_color_hex(hex_color, tolerance_h=tol, s_min=s_min, v_min=v_min)
				await websocket.send_json({"type": "ok"})
			elif kind == "set_params":
				processor.set_params(
					blur_ksize=message.get("blur_ksize"),
					morph_iterations=message.get("morph_iterations"),
					morph_kernel_size=message.get("morph_kernel_size"),
					preview_mask=message.get("preview_mask"),
					keep_largest=message.get("keep_largest"),
					min_area_ratio=message.get("min_area_ratio"),
					skin_protect=message.get("skin_protect"),
				)
				await websocket.send_json({"type": "ok"})
	except WebSocketDisconnect:
		return
