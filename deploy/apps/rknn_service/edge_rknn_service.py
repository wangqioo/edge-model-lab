#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

import numpy as np
from rknnlite.api import RKNNLite


def parse_count(raw_count: str | None, default: int = 10, minimum: int = 1, maximum: int = 200) -> int:
    if raw_count is None:
        return default
    try:
        count = int(raw_count)
    except ValueError:
        return minimum
    return max(minimum, min(maximum, count))


def summarize_latencies(latencies_ms: list[float]) -> dict[str, float | int]:
    sorted_latencies = sorted(latencies_ms)

    def percentile(percent: float) -> float:
        index = int(((len(sorted_latencies) - 1) * percent) + 0.999999)
        return round(sorted_latencies[index], 3)

    return {
        "count": len(sorted_latencies),
        "min_ms": round(sorted_latencies[0], 3),
        "avg_ms": round(sum(sorted_latencies) / len(sorted_latencies), 3),
        "p50_ms": percentile(0.50),
        "p95_ms": percentile(0.95),
        "max_ms": round(sorted_latencies[-1], 3),
    }


class RknnService:
    def __init__(self, model_path: str) -> None:
        self.model_path = model_path
        self.started_at = time.time()
        self.rknn = RKNNLite()
        load_start = time.time()
        self.load_ret = self.rknn.load_rknn(model_path)
        if self.load_ret != 0:
            raise RuntimeError(f"load_rknn failed: {self.load_ret}")
        self.init_ret = self.rknn.init_runtime(core_mask=RKNNLite.NPU_CORE_0)
        if self.init_ret != 0:
            raise RuntimeError(f"init_runtime failed: {self.init_ret}")
        self.load_init_ms = int((time.time() - load_start) * 1000)
        self.inference_count = 0
        self.last_inference_ms: float | None = None
        self._inference_lock = threading.Lock()

    def health(self) -> dict[str, Any]:
        return {
            "ok": True,
            "model_path": self.model_path,
            "load_ret": self.load_ret,
            "init_ret": self.init_ret,
            "load_init_ms": self.load_init_ms,
            "uptime_s": int(time.time() - self.started_at),
            "inference_count": self.inference_count,
            "last_inference_ms": self.last_inference_ms,
        }

    def infer_synthetic(self) -> dict[str, Any]:
        input_data = np.zeros((1, 224, 224, 3), dtype=np.uint8)
        started = time.time()
        with self._inference_lock:
            outputs = self.rknn.inference(inputs=[input_data])
        elapsed_ms = (time.time() - started) * 1000
        self.inference_count += 1
        self.last_inference_ms = round(elapsed_ms, 3)
        shapes = []
        if outputs is not None:
            shapes = [list(output.shape) for output in outputs]
        return {
            "ok": outputs is not None,
            "elapsed_ms": self.last_inference_ms,
            "output_shapes": shapes,
            "output_count": len(outputs) if outputs is not None else 0,
        }

    def bench_synthetic(self, count: int) -> dict[str, Any]:
        latencies_ms = []
        output_shapes = []
        for _ in range(count):
            result = self.infer_synthetic()
            if not result["ok"]:
                return {"ok": False, "error": "inference returned no outputs"}
            latencies_ms.append(float(result["elapsed_ms"]))
            output_shapes = result["output_shapes"]
        return {
            "ok": True,
            "output_shapes": output_shapes,
            **summarize_latencies(latencies_ms),
        }


def make_handler(service: RknnService) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

        def _json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self._json(200, service.health())
                return
            if parsed.path == "/infer/synthetic":
                try:
                    self._json(200, service.infer_synthetic())
                except Exception as exc:
                    self._json(500, {"ok": False, "error": f"{type(exc).__name__}: {exc}"})
                return
            if parsed.path == "/bench/synthetic":
                try:
                    query = parse_qs(parsed.query)
                    count = parse_count(query.get("count", [None])[0])
                    self._json(200, service.bench_synthetic(count))
                except Exception as exc:
                    self._json(500, {"ok": False, "error": f"{type(exc).__name__}: {exc}"})
                return
            self._json(404, {"ok": False, "error": "not found"})

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18080)
    args = parser.parse_args()

    service = RknnService(args.model)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(service))
    print(
        json.dumps(
            {
                "event": "started",
                "host": args.host,
                "port": args.port,
                "model": args.model,
                "load_init_ms": service.load_init_ms,
            },
            sort_keys=True,
        ),
        flush=True,
    )
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
