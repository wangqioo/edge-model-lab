from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


def load_service_module():
    fake_rknnlite = types.ModuleType("rknnlite")
    fake_api = types.ModuleType("rknnlite.api")

    class FakeRKNNLite:
        NPU_CORE_0 = 1

    fake_api.RKNNLite = FakeRKNNLite
    sys.modules["rknnlite"] = fake_rknnlite
    sys.modules["rknnlite.api"] = fake_api

    path = Path(__file__).resolve().parents[1] / "deploy/apps/rknn_service/edge_rknn_service.py"
    spec = importlib.util.spec_from_file_location("edge_rknn_service_for_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RknnServiceBenchTests(unittest.TestCase):
    def test_parse_count_clamps_values(self) -> None:
        module = load_service_module()

        self.assertEqual(module.parse_count("7"), 7)
        self.assertEqual(module.parse_count("0"), 1)
        self.assertEqual(module.parse_count("-3"), 1)
        self.assertEqual(module.parse_count("1000"), 200)
        self.assertEqual(module.parse_count("bad"), 1)
        self.assertEqual(module.parse_count(None), 10)

    def test_summarize_latencies_uses_nearest_rank_percentiles(self) -> None:
        module = load_service_module()

        summary = module.summarize_latencies([10.1111, 20.2222, 30.3333, 40.4444, 50.5555])

        self.assertEqual(
            summary,
            {
                "count": 5,
                "min_ms": 10.111,
                "avg_ms": 30.333,
                "p50_ms": 30.333,
                "p95_ms": 50.556,
                "max_ms": 50.556,
            },
        )


if __name__ == "__main__":
    unittest.main()
