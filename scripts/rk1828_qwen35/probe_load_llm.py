#!/usr/bin/env python3
"""Probe RKNN3 load_llm for a Qwen3.5 ONNX variant."""

import os

from rknn.api import RKNN

CHUNK = os.environ.get("QWEN35_CHUNK_SIZE", "8")
SUFFIX = os.environ.get("QWEN35_SUFFIX") or f"llm_chunk{CHUNK}"
BASE = os.environ.get(
    "QWEN35_BASE_OUT",
    "/home/wq/edge-model-lab/models/artifacts/rk1828/qwen35-4b",
)
ONNX_MODEL = os.environ.get("QWEN35_ONNX", f"{BASE}/{SUFFIX}/Qwen3.5-4B-llm.onnx")
LLM_CONFIG = os.environ.get("QWEN35_LLM_CONFIG", f"{BASE}/llm/Qwen3.5-4B-llm.config.pkl")
SEQ_LENS = [int(value) for value in os.environ.get("QWEN35_SEQ_LENS", "1,128").split(",")]


def main():
    print(
        "probe_load_llm",
        "chunk",
        CHUNK,
        "suffix",
        SUFFIX,
        "onnx",
        ONNX_MODEL,
        "seq_lens",
        SEQ_LENS,
        flush=True,
    )
    rknn = RKNN(verbose=True)
    rknn.config(
        target_platform="rk1820",
        quantized_dtype="w4a16",
        quantized_algorithm="grq",
        quantized_method="group32",
    )
    ret = rknn.load_llm(model=ONNX_MODEL, config=LLM_CONFIG, seq_lens=SEQ_LENS)
    print("load_llm_ret", ret, flush=True)
    rknn.release()
    raise SystemExit(ret)


if __name__ == "__main__":
    main()
