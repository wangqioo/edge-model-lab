from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def load_module():
    path = Path(__file__).resolve().parents[1] / "deploy/apps/rk1828/qwen25_omni_vlm_web.py"
    spec = importlib.util.spec_from_file_location("qwen25_omni_vlm_web_for_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Qwen25OmniVlmWebTests(unittest.TestCase):
    def test_parse_demo_output_extracts_answer_and_metrics(self) -> None:
        module = load_module()
        stdout = """
--> init qwen2_5_omni vision model
月球上，宇航员正在打开啤酒瓶。
 Prefill       315.24           247       1.28                     783.53
 Generate      147.97           12        12.33                    81.10
 Vision latency = 240.90 ms, FPS = 4.15
"""

        parsed = module.parse_demo_output(stdout)

        self.assertEqual(parsed["answer"], "月球上，宇航员正在打开啤酒瓶。")
        self.assertEqual(
            parsed["metrics"],
            [
                "Prefill       315.24           247       1.28                     783.53",
                "Generate      147.97           12        12.33                    81.10",
                "Vision latency = 240.90 ms, FPS = 4.15",
            ],
        )

    def test_render_page_escapes_model_output(self) -> None:
        module = load_module()

        html = module.render_page(result={"answer": "<script>alert(1)</script>", "metrics": [], "raw": ""})

        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertNotIn("<script>alert(1)</script>", html)

    def test_allowed_upload_accepts_images_only(self) -> None:
        module = load_module()

        self.assertTrue(module.allowed_upload("demo.jpg", "image/jpeg"))
        self.assertTrue(module.allowed_upload("demo.png", "image/png"))
        self.assertFalse(module.allowed_upload("demo.txt", "text/plain"))
        self.assertFalse(module.allowed_upload("demo.jpg", "text/plain"))


if __name__ == "__main__":
    unittest.main()
