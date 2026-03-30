import unittest

import numpy as np

from app.services.processor import FrameProcessor


class FrameProcessorTests(unittest.TestCase):
    def test_clear_background_resets_state(self):
        processor = FrameProcessor()
        frame = np.zeros((20, 20, 3), dtype=np.uint8)

        processor.set_background(frame)
        processor.clear_background()

        self.assertFalse(processor.background_ready)
        self.assertIsNone(processor.cloak.background_frame)

    def test_decode_base64_rejects_non_image_data_uri(self):
        data_uri = "data:text/plain;base64,SGVsbG8="
        self.assertIsNone(FrameProcessor.decode_base64_image(data_uri))
