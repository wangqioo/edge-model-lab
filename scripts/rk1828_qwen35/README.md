# RK1828 Qwen3.5 Conversion Probes

These scripts record the RK1828 RKNN3 conversion probes for
`Qwen/Qwen3.5-4B`.

They are meant to run on the home Linux server, not on the Mac control
machine. The generated ONNX/RKNN3 files are too large for git and stay under:

```text
/home/wq/edge-model-lab/models/artifacts/rk1828/qwen35-4b
```

## Environments

Use separate Python environments:

```text
/home/wq/edge-tools/qwen35-rkllm130-py310
/home/wq/edge-tools/rknn3-qwen3vl-py310
```

`qwen35-rkllm130-py310` recognizes `Qwen3_5ForConditionalGeneration` and is
used for ONNX export. `rknn3-qwen3vl-py310` contains `rknn.api.RKNN` and is used
for RKNN3 `load_llm` probes.

## Scripts

- `export_llm_onnx_chunk_sweep.py`: exports Qwen3.5 LLM ONNX with a forced
  `GatedDeltaNet` chunk size and optional static prompt shape.
- `probe_load_llm.py`: runs only `rknn.load_llm`, so failures are isolated
  before `rknn.build`.
- `analyze_onnx_patterns.py`: counts ONNX nodes by Qwen3.5 layer and shows the
  source of graph expansion.
- `optimize_static_onnx.py`: records the attempted full-graph
  onnxoptimizer/onnxsim path. It is kept for reproducibility, but it is not
  practical on the current 32 GiB server.

## Reproduction

Copy this directory to the server or run the equivalent files already staged
under `/home/wq/edge-tools`.

Export a smaller fallback ONNX:

```bash
QWEN35_CHUNK_SIZE=8 \
/home/wq/edge-tools/qwen35-rkllm130-py310/bin/python \
  scripts/rk1828_qwen35/export_llm_onnx_chunk_sweep.py
```

Export a static 16-token prompt with dynamic `position_ids`:

```bash
QWEN35_CHUNK_SIZE=8 \
QWEN35_STATIC_SHAPE=1 \
QWEN35_PROMPT_SIZE=16 \
QWEN35_POSITION_DYNAMIC=1 \
/home/wq/edge-tools/qwen35-rkllm130-py310/bin/python \
  scripts/rk1828_qwen35/export_llm_onnx_chunk_sweep.py
```

Probe RKNN3 loading:

```bash
QWEN35_SUFFIX=llm_chunk8_static16_posdyn \
/home/wq/edge-tools/rknn3-qwen3vl-py310/bin/python \
  scripts/rk1828_qwen35/probe_load_llm.py
```

Analyze the ONNX graph:

```bash
QWEN35_ONNX=/home/wq/edge-model-lab/models/artifacts/rk1828/qwen35-4b/llm_chunk8_static64/Qwen3.5-4B-llm.onnx \
/home/wq/edge-tools/qwen35-rkllm130-py310/bin/python \
  scripts/rk1828_qwen35/analyze_onnx_patterns.py
```

## Current Result

The best fallback ONNX path tested still does not produce an RKNN3 LLM artifact.
The graph is dominated by Qwen3.5 `linear_attention` fallback expansion:

```text
24 linear_attention layers, about 1,701-1,733 nodes per layer
8 full_attention layers, about 282 nodes per layer
```

Static prompt and chunk-size reductions reduce the graph from 212,293 nodes to
about 41k-55k nodes, but `rknn.load_llm` still fills the 32 GiB server memory
when `position_ids` remains dynamic enough for RKNN3 RoPE replacement. A fully
static `position_ids` export fails earlier because RKNN3 requires a dynamic axis
for `position_ids`.
