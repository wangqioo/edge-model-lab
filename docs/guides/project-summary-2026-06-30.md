# Edge Model Lab Summary, 2026-06-30

This document summarizes the current project state after the three-board edge model deployment work.

## What Was Built

`edge-model-lab` is now the control repository for deploying and validating edge-side AI workloads on three Rockchip boards:

- `orange-rk3588`: Orange Pi RK3588, 16GB RAM, primary multimodal LLM target.
- `linaro-rk3576`: RK3576, 8GB RAM, main RK3576 validation target.
- `lckfb-rk3576`: RK3576, 4GB RAM, low-memory boundary target.

The repository contains:

- device inventory and audit reports
- model asset metadata without large model blobs
- `edgectl` commands for health checks, deployment, smoke tests, logs, and benchmarks
- experiment notes for each deployment milestone
- beginner-oriented runbooks and troubleshooting notes

Large model files stay outside git on the Mac, Linux server, or target boards.

## Current Model Status

| Device | Model | Status |
| --- | --- | --- |
| `orange-rk3588` | `Qwen/Qwen3.5-4B` | Converted to RKNN + RKLLM, deployed, board-tested with image Q&A |
| `orange-rk3588` | `Qwen3-VL-4B-Instruct` | Converted earlier, deployed, board-tested |
| `orange-rk3588` | `Qwen1.5` text RKLLM | Working baseline |
| `linaro-rk3576` | `Qwen3-VL-2B-Instruct` vendor RK3576 bundle | Deployed and smoke-tested |
| `lckfb-rk3576` | `Qwen3-VL-2B-Instruct` vendor RK3576 bundle | Deployment path works; generation is limited by 4GB RAM |
| `linaro-rk3576` | YOLOv5 RKNN demo | Deployed as a systemd smoke unit |
| `linaro-rk3576`, `lckfb-rk3576` | Python RKNN HTTP service | Deployment and benchmark path exists |

## Qwen3.5-4B RK3588 Result

The newest completed milestone is `Qwen/Qwen3.5-4B` multimodal deployment on Orange Pi RK3588.

Server workspace:

```text
/home/wq/edge-workspaces/rkllm-qwen35-4b-rk3588-v130
```

Source model:

```text
/home/wq/edge-model-sources/huggingface/Qwen/Qwen3.5-4B
```

Rockchip toolchain:

```text
/home/wq/edge-tools/rknn-llm-release-v1.3.0
```

Generated artifacts:

```text
rknn/qwen3.5_vision_rk3588.rknn          704579761 bytes
rkllm/qwen3.5-4b_w8a8_rk3588.rkllm       5540941884 bytes
```

Board deployment:

```text
/home/orangepi/edge-model-lab/qwen35-4b-rk3588
```

Verified board state:

```text
rkllm-runtime: 1.3.0
RKNPU driver: 0.9.8
target platform: RK3588
vision input: 448x448
vision tokens: 196
language model dtype: W8A8
NPU cores: 3
```

Validation:

- The default Rockchip demo image loaded and generated a correct English description.
- `/Users/wq/Desktop/111.jpg` loaded and generated a correct Chinese description of the lake, sunset/sunrise, clouds, light rays, water reflection, and distant skyline.

Important caveat:

- The vision RKNN export logged `REGTASK` and `Unknown op target` compiler warnings.
- The generated `.rknn` still loaded and ran successfully on the RK3588 board.
- Keep this warning in the record because a future driver, runtime, or resolution change may expose it again.

Detailed record:

```text
docs/experiments/2026-06-30-rk3588-qwen35-4b-conversion.md
```

## Repeatable Commands

List devices:

```bash
./scripts/edgectl list
```

Health-check all devices:

```bash
./scripts/edgectl health all
```

List model metadata:

```bash
./scripts/edgectl models
./scripts/edgectl models --platform rk3588
./scripts/edgectl models --platform rk3576
```

Smoke-test deployed Qwen3-VL-4B on RK3588:

```bash
EDGE_ORANGE_RK3588_PASSWORD='...' ./scripts/edgectl rk3588-qwen3-vl-smoke orange-rk3588
```

Deploy or smoke RK3576 Qwen3-VL-2B vendor bundles:

```bash
EDGE_LINARO_RK3576_PASSWORD='...' ./scripts/edgectl llm-deploy linaro-rk3576
EDGE_LCKFB_RK3576_PASSWORD='...' ./scripts/edgectl llm-deploy lckfb-rk3576
```

## Lessons Learned

Rockchip model deployment is a system problem, not only a model conversion problem. The model artifact, runtime library, board kernel, RKNPU driver, CMA memory reservation, and NPU target platform all have to match.

For multimodal models, the deployable unit is normally split:

- `.rknn` for the vision encoder/projector
- `.rkllm` for the language model
- a matching board runtime/demo binary
- correct image placeholder tokens such as `<|vision_start|>`, `<|vision_end|>`, and `<|image_pad|>`

For new models, use this order:

1. Confirm model family support in the Rockchip RKLLM release.
2. Download source weights onto the Linux server, not into git.
3. Export vision ONNX.
4. Convert vision ONNX to RKNN.
5. Generate LLM calibration inputs.
6. Export LLM to RKLLM.
7. Build the matching board demo against the same RKLLM runtime version.
8. Copy artifacts to the board with resumable transfer.
9. Test with a known demo image and then a real user image.
10. Record exact paths, file sizes, warnings, and board output.

## Next Best Work

The project is ready for the next phase:

1. Add an `edgectl` command for the Qwen3.5-4B RK3588 bundle.
2. Replace interactive vendor demos with non-interactive wrappers.
3. Add benchmark capture for load time, first token latency, tokens per second, memory, and temperature.
4. Convert the deployment notes into one-command deploy flows for all three boards.
5. Move SSH access to keys and remove password fallback from normal workflows.
