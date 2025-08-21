import base64
import binascii
import cv2
import numpy as np
from typing import Optional, List, Tuple
from ..cv.invisibility import InvisibilityCloak

class FrameProcessor:
	def __init__(self, lower_hsv=(0, 120, 70), upper_hsv=(10, 255, 255)):
		self.cloak = InvisibilityCloak(lower_hsv=lower_hsv, upper_hsv=upper_hsv)
		self.background_ready = False
		self.current_ranges: List[Tuple[Tuple[int, int, int], Tuple[int, int, int]]] = [(lower_hsv, upper_hsv)]
		self.preview_mask: bool = False
		self._just_captured: bool = False

	def set_background(self, frame_bgr: np.ndarray) -> None:
		self.cloak.capture_background(frame_bgr)
		self.background_ready = True
		self._just_captured = True

	def pop_just_captured(self) -> bool:
		flag = self._just_captured
		self._just_captured = False
		return flag

	def set_color_hex(self, hex_color: str, tolerance_h: int = 10, s_min: int = 120, v_min: int = 70) -> None:
		h = hex_color.lstrip('#')
		r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
		bgr = np.uint8([[[b, g, r]]])
		hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[0][0]
		hue = int(hsv[0])
		low_s, low_v = s_min, v_min
		ranges: List[Tuple[Tuple[int, int, int], Tuple[int, int, int]]] = []
		lo_h = (hue - tolerance_h) % 180
		hi_h = (hue + tolerance_h) % 180
		if lo_h <= hi_h:
			ranges.append(((lo_h, low_s, low_v), (hi_h, 255, 255)))
		else:
			ranges.append(((0, low_s, low_v), (hi_h, 255, 255)))
			ranges.append(((lo_h, low_s, low_v), (179, 255, 255)))
		self.current_ranges = ranges
		self.cloak.set_target_ranges(ranges)

	def set_params(self, blur_ksize: Optional[int] = None, morph_iterations: Optional[int] = None, morph_kernel_size: Optional[int] = None, preview_mask: Optional[bool] = None, keep_largest: Optional[bool] = None, min_area_ratio: Optional[float] = None, skin_protect: Optional[bool] = None) -> None:
		self.cloak.set_params(blur_ksize=blur_ksize, morph_iterations=morph_iterations, morph_kernel_size=morph_kernel_size)
		self.cloak.set_filters(keep_largest=keep_largest, min_area_ratio=min_area_ratio, skin_protect=skin_protect)
		if preview_mask is not None:
			self.preview_mask = bool(preview_mask)

	def process_frame(self, frame_bgr: np.ndarray) -> np.ndarray:
		if not self.background_ready:
			self.set_background(frame_bgr)
		if self.preview_mask:
			mask = self.cloak.build_mask(frame_bgr)
			mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
			overlay = frame_bgr.copy()
			overlay[mask > 0] = (0, 255, 0)
			combined = cv2.addWeighted(frame_bgr, 0.6, overlay, 0.4, 0)
			return combined
		return self.cloak.apply(frame_bgr)

	@staticmethod
	def decode_base64_image(data_uri: str) -> Optional[np.ndarray]:
		if not data_uri or not isinstance(data_uri, str):
			return None
		
		if "," in data_uri:
			header, b64data = data_uri.split(",", 1)
			# Basic validation of data URI format
			if not header.startswith("data:image/"):
				return None
		else:
			b64data = data_uri
			
		try:
			binary = base64.b64decode(b64data, validate=True)
			# Check for reasonable image size limits (max 50MB decoded)
			if len(binary) > 50 * 1024 * 1024:
				return None
			
			np_arr = np.frombuffer(binary, np.uint8)
			frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
			
			# Additional validation: ensure decoded image is reasonable
			if frame is not None:
				h, w = frame.shape[:2]
				if h > 4000 or w > 4000 or h < 10 or w < 10:
					return None
					
			return frame
		except (base64.binascii.Error, ValueError, cv2.error) as e:
			return None
		except Exception:
			return None

	@staticmethod
	def encode_base64_image(frame_bgr: np.ndarray) -> str:
		ok, buf = cv2.imencode('.jpg', frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
		if not ok:
			return ""
		b64 = base64.b64encode(buf).decode('ascii')
		return f"data:image/jpeg;base64,{b64}"
