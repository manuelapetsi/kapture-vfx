import cv2
import numpy as np
from typing import Tuple, Optional, List

class InvisibilityCloak:
	def __init__(self, lower_hsv: Tuple[int, int, int], upper_hsv: Tuple[int, int, int]):
		self.hsv_ranges: List[Tuple[np.ndarray, np.ndarray]] = [
			(np.array(lower_hsv, dtype=np.uint8), np.array(upper_hsv, dtype=np.uint8))
		]
		self.background_frame: Optional[np.ndarray] = None
		self.blur_ksize: int = 5
		self.morph_iterations: int = 2
		self.morph_kernel: np.ndarray = np.ones((3, 3), np.uint8)
		# Filters
		self.keep_largest: bool = False
		self.min_area_ratio: float = 0.0  # 0..1 of frame area
		self.skin_protect: bool = False

	def set_target_ranges(self, ranges: List[Tuple[Tuple[int, int, int], Tuple[int, int, int]]]) -> None:
		self.hsv_ranges = [
			(np.array(lo, dtype=np.uint8), np.array(hi, dtype=np.uint8)) for lo, hi in ranges
		]

	def set_params(self, blur_ksize: Optional[int] = None, morph_iterations: Optional[int] = None, morph_kernel_size: Optional[int] = None) -> None:
		if blur_ksize is not None and blur_ksize % 2 == 1:
			self.blur_ksize = max(3, blur_ksize)
		if morph_iterations is not None:
			self.morph_iterations = max(1, morph_iterations)
		if morph_kernel_size is not None and morph_kernel_size % 2 == 1:
			k = max(3, morph_kernel_size)
			self.morph_kernel = np.ones((k, k), np.uint8)

	def set_filters(self, keep_largest: Optional[bool] = None, min_area_ratio: Optional[float] = None, skin_protect: Optional[bool] = None) -> None:
		if keep_largest is not None:
			self.keep_largest = bool(keep_largest)
		if min_area_ratio is not None:
			self.min_area_ratio = max(0.0, min(1.0, float(min_area_ratio)))
		if skin_protect is not None:
			self.skin_protect = bool(skin_protect)

	def capture_background(self, frame: np.ndarray) -> None:
		self.background_frame = frame.copy()

	def _apply_filters(self, mask: np.ndarray, frame: np.ndarray) -> np.ndarray:
		filtered = mask.copy()
		# Remove tiny blobs by area threshold
		if self.min_area_ratio > 0:
			min_area = int(self.min_area_ratio * mask.shape[0] * mask.shape[1])
			contours, _ = cv2.findContours(filtered, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
			filtered[:] = 0
			for cnt in contours:
				if cv2.contourArea(cnt) >= min_area:
					cv2.drawContours(filtered, [cnt], -1, 255, thickness=cv2.FILLED)
		# Keep only the largest connected component
		if self.keep_largest:
			num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(filtered)
			if num_labels > 1:
				# label 0 is background; find largest non-zero
				areas = stats[1:, cv2.CC_STAT_AREA]
				largest_label = 1 + int(np.argmax(areas))
				filtered = np.where(labels == largest_label, 255, 0).astype(np.uint8)
		# Protect skin regions by subtracting a skin mask
		if self.skin_protect:
			ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
			# Generic skin range (tuneable)
			lower = np.array([0, 135, 80], dtype=np.uint8)
			upper = np.array([255, 180, 135], dtype=np.uint8)
			skin = cv2.inRange(ycrcb, lower, upper)
			filtered = cv2.bitwise_and(filtered, cv2.bitwise_not(skin))
		return filtered

	def build_mask(self, frame: np.ndarray) -> np.ndarray:
		# Light blur for robustness
		ks = self.blur_ksize if self.blur_ksize % 2 == 1 else self.blur_ksize + 1
		blurred = cv2.GaussianBlur(frame, (ks, ks), 0)
		hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
		mask_total = None
		for lower_hsv, upper_hsv in self.hsv_ranges:
			mask = cv2.inRange(hsv, lower_hsv, upper_hsv)
			mask_total = mask if mask_total is None else cv2.bitwise_or(mask_total, mask)
		if mask_total is None:
			mask_total = np.zeros(frame.shape[:2], dtype=np.uint8)
		# Morphological cleanup
		mask_total = cv2.morphologyEx(mask_total, cv2.MORPH_OPEN, self.morph_kernel, iterations=self.morph_iterations)
		mask_total = cv2.dilate(mask_total, self.morph_kernel, iterations=1)
		# Post-filters
		mask_total = self._apply_filters(mask_total, frame)
		return mask_total

	def apply(self, frame: np.ndarray) -> np.ndarray:
		if self.background_frame is None:
			return frame
		mask_total = self.build_mask(frame)
		# Ensure background matches current frame size to avoid OpenCV mask mismatch
		if self.background_frame.shape[:2] != frame.shape[:2]:
			bg = cv2.resize(self.background_frame, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_LINEAR)
		else:
			bg = self.background_frame
		inverse_mask = cv2.bitwise_not(mask_total)
		res1 = cv2.bitwise_and(bg, bg, mask=mask_total)
		res2 = cv2.bitwise_and(frame, frame, mask=inverse_mask)
		final = cv2.addWeighted(res1, 1, res2, 1, 0)
		return final
