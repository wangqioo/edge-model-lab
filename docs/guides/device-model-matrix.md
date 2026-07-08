# Device and Model Matrix

This document answers "what is deployed where?".

## Device Matrix

| id | SSH | chip | memory | current role | best use |
| --- | --- | --- | ---: | --- | --- |
| `orange-rk3588` | `orangepi@150.158.146.192:6280` or `orangepi@192.168.1.52` | RK3588 | 16G | primary deployment | Qwen3.5-4B multimodal, Qwen3-VL-4B multimodal, RK3588 RKNN/RKLLM validation |
| RK1828 M.2 accelerator | attached to `orange-rk3588` host | RK1828 | separate 12V power required | RKNN3 acceleration for Qwen3-VL-4B; PCIe detection works after RK1828-first power sequence; runtime blocked by missing RK3588 host RKEP kernel support |
| `linaro-rk3576` | `linaro@150.158.146.192:6276` | RK3576 | 8G | main RK3576 board | Qwen3-VL-2B RK3576, RKNN service, YOLO |
| `lckfb-rk3576` | `lckfb@150.158.146.192:6277` | RK3576 | 4G | low-memory board | low-memory failure/limit validation |

## Model Matrix

| board | model | format | status | command |
| --- | --- | --- | --- | --- |
| RK1828 M.2 accelerator | Qwen3-VL-4B-Instruct | RKNN3 + weights | conversion complete; PCIe endpoint detected; runtime blocked by host kernel missing `CONFIG_PCIE_FUNC_RKEP` | see `docs/guides/rk1828-qwen3-vl-4b-runbook.md` |
| `orange-rk3588` | Qwen3.5-4B | RKLLM + RKNN | working, board-tested with demo and user image | manual smoke in `docs/experiments/2026-06-30-rk3588-qwen35-4b-conversion.md` |
| `orange-rk3588` | Qwen3-VL-4B-Instruct | RKLLM + RKNN | working | `edgectl rk3588-qwen3-vl-smoke orange-rk3588` |
| `orange-rk3588` | Qwen1.5 text demo | RKLLM | working baseline | `edgectl llm-deploy orange-rk3588` |
| `orange-rk3588` | RKNN Lite Mobilenet/Resnet | RKNN | runtime baseline | `edgectl rknn-smoke orange-rk3588 <asset>` |
| `linaro-rk3576` | Qwen3-VL-2B-Instruct | RKLLM + RKNN | working, better RK3576 target | `edgectl llm-deploy linaro-rk3576` |
| `lckfb-rk3576` | Qwen3-VL-2B-Instruct | RKLLM + RKNN | deployment works, memory constrained | `edgectl llm-deploy lckfb-rk3576` |
| `linaro-rk3576` | YOLOv5s demo | RKNN | working smoke path | `edgectl yolo-deploy linaro-rk3576` |
| `linaro-rk3576`, `lckfb-rk3576` | Python RKNN service | RKNN | service skeleton exists | `edgectl rknn-service-deploy <device>` |

## Artifact Rules

RK3576 and RK3588 artifacts are not interchangeable.
RKNN3 RK1828 artifacts are also separate from RKNN/RKLLM RK3576/RK3588 artifacts.

Examples:

```text
qwen3-vl-4b-instruct_w8a8_rk3576.rkllm  -> RK3576 only
qwen3-vl-4b-instruct_w8a8_rk3588.rkllm  -> RK3588 only
qwen3-vl_vision_rk3576.rknn             -> RK3576 only
qwen3-vl_vision_rk3588.rknn             -> RK3588 only
Qwen3-VL-4B-llm-rk1828.rknn + .weight   -> RK1828 RKNN3 only
```

## Current Recommendation

Use the boards like this:

1. Develop and validate new multimodal ideas first on `orange-rk3588`.
2. Bring up RK1828 with RK1828 12V powered before RK3588 boot, then resolve the RK3588 host RKEP kernel requirement before model runtime testing.
3. Validate smaller RK3576-compatible models on `linaro-rk3576`.
4. Use `lckfb-rk3576` only after the 8G RK3576 board works, to understand low-memory constraints.

Do not use the 4G TaishanPi as the first target for a new LLM deployment.
