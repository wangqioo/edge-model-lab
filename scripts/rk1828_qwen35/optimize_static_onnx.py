#!/usr/bin/env python3
"""Attempt full-graph ONNX cleanup for a static Qwen3.5 export.

This path was tried for evidence gathering. On the current 32 GiB server it
balloons into memory pressure before producing a useful optimized artifact.
"""

import collections
import os
import shutil
from pathlib import Path

import onnx
import onnxoptimizer
from onnxsim import simplify

SRC = Path(
    os.environ.get(
        "QWEN35_OPT_SRC",
        "/home/wq/edge-model-lab/models/artifacts/rk1828/qwen35-4b/llm_chunk8_static64",
    )
)
DST = Path(
    os.environ.get(
        "QWEN35_OPT_DST",
        "/home/wq/edge-model-lab/models/artifacts/rk1828/qwen35-4b/llm_chunk8_static64_opt",
    )
)


def count(model):
    return collections.Counter(node.op_type for node in model.graph.node)


def report(label, model):
    op_counts = count(model)
    print(label, "nodes", len(model.graph.node), "initializers", len(model.graph.initializer), flush=True)
    print(label, op_counts.most_common(20), flush=True)


def main():
    if DST.exists():
        shutil.rmtree(DST)
    DST.mkdir(parents=True)

    src_model = SRC / "Qwen3.5-4B-llm.onnx"
    cwd = os.getcwd()
    os.chdir(SRC)
    model = onnx.load(src_model.name, load_external_data=True)
    report("original", model)

    passes = [
        "eliminate_nop_cast",
        "eliminate_nop_dropout",
        "eliminate_nop_flatten",
        "eliminate_nop_monotone_argmax",
        "eliminate_nop_pad",
        "eliminate_nop_transpose",
        "eliminate_unused_initializer",
        "extract_constant_to_initializer",
        "fuse_add_bias_into_conv",
        "fuse_bn_into_conv",
        "fuse_consecutive_concats",
        "fuse_consecutive_log_softmax",
        "fuse_consecutive_reduce_unsqueeze",
        "fuse_consecutive_squeezes",
        "fuse_consecutive_transposes",
        "fuse_matmul_add_bias_into_gemm",
        "fuse_pad_into_conv",
        "fuse_transpose_into_gemm",
    ]
    model = onnxoptimizer.optimize(model, passes)
    report("onnxoptimizer", model)

    model, ok = simplify(model, check_n=0, perform_optimization=True, skip_fuse_bn=True)
    print("onnxsim_ok", ok, flush=True)
    report("onnxsim", model)

    os.chdir(DST)
    onnx.save_model(
        model,
        "Qwen3.5-4B-llm.onnx",
        save_as_external_data=True,
        all_tensors_to_one_file=False,
        size_threshold=1024,
    )
    onnx.checker.check_model("Qwen3.5-4B-llm.onnx")
    os.chdir(cwd)
    print("saved", DST, flush=True)


if __name__ == "__main__":
    main()
