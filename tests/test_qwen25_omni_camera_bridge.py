from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


def load_module():
    path = Path(__file__).resolve().parents[1] / "deploy/apps/rk1828/qwen25_omni_camera_bridge.py"
    spec = importlib.util.spec_from_file_location("qwen25_omni_camera_bridge_for_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Qwen25OmniCameraBridgeTests(unittest.TestCase):
    def test_render_camera_page_uses_camera_speech_and_local_infer(self) -> None:
        module = load_module()

        html = module.render_camera_page("http://127.0.0.1:8892")

        self.assertIn("navigator.mediaDevices.getUserMedia", html)
        self.assertIn("SpeechRecognition", html)
        self.assertIn("speechSynthesis", html)
        self.assertIn("fetch('/infer'", html)

    def test_build_multipart_body_contains_image_and_prompt(self) -> None:
        module = load_module()

        body, content_type = module.build_multipart_body(
            image_name="frame.jpg",
            image_content_type="image/jpeg",
            image_data=b"abc",
            prompt="看到了什么？",
        )

        self.assertIn("multipart/form-data; boundary=", content_type)
        self.assertIn(b'name="image"; filename="frame.jpg"', body)
        self.assertIn(b"Content-Type: image/jpeg", body)
        self.assertIn(b"abc", body)
        self.assertIn("看到了什么？".encode("utf-8"), body)

    def test_bridge_health_payload_names_board_url(self) -> None:
        module = load_module()

        payload = module.health_payload("http://board:8892")

        self.assertEqual(json.loads(json.dumps(payload)), {"ok": True, "board_base_url": "http://board:8892"})


if __name__ == "__main__":
    unittest.main()
