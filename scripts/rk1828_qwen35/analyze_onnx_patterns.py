#!/usr/bin/env python3
"""Summarize Qwen3.5 ONNX graph expansion by layer."""

import collections
import os
from pathlib import Path

import onnx

DEFAULT_MODEL = (
    "/home/wq/edge-model-lab/models/artifacts/rk1828/qwen35-4b/"
    "llm_chunk8_static64/Qwen3.5-4B-llm.onnx"
)


def layer_key(node_name):
    parts = [part for part in node_name.split("/") if part]
    if len(parts) >= 3 and parts[0] == "language_model" and parts[1].startswith("layers."):
        return "/".join(parts[:3])
    if len(parts) >= 2 and parts[0] == "language_model" and parts[1].startswith("layers."):
        return "/".join(parts[:2])
    return "<other>"


def layer_number(node_name):
    parts = [part for part in node_name.split("/") if part]
    if len(parts) >= 2 and parts[0] == "language_model" and parts[1].startswith("layers."):
        return parts[1].split(".", 1)[1]
    return None


def main():
    model_path = Path(os.environ.get("QWEN35_ONNX", DEFAULT_MODEL))
    model = onnx.load(model_path, load_external_data=False)
    nodes = list(model.graph.node)

    print("model", model_path, flush=True)
    print("nodes", len(nodes), "initializers", len(model.graph.initializer), flush=True)

    by_prefix = collections.Counter()
    op_by_layer = collections.defaultdict(collections.Counter)

    for node in nodes:
        name = node.name or (node.output[0] if node.output else "")
        by_prefix[layer_key(name)] += 1
        layer = layer_number(name)
        if layer is not None:
            op_by_layer[layer][node.op_type] += 1

    print("top_prefixes", by_prefix.most_common(80), flush=True)

    for layer in sorted(op_by_layer, key=lambda value: int(value) if value.isdigit() else 999):
        total = sum(op_by_layer[layer].values())
        print("layer", layer, "total", total, op_by_layer[layer].most_common(15), flush=True)

    inputs = [
        (value.name, [dim.dim_value or dim.dim_param for dim in value.type.tensor_type.shape.dim])
        for value in model.graph.input
    ]
    print("inputs", inputs, flush=True)
    print("outputs", [value.name for value in model.graph.output], flush=True)


if __name__ == "__main__":
    main()
