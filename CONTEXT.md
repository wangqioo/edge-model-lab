# Edge Model Lab Context

## Purpose

Edge Model Lab is the operating repo for edge AI model work across the Mac control machine, the home Linux server, and Rockchip devices.

The repo is not a model-weight store. It records device inventory, conversion decisions, deployment commands, smoke-test results, and the paths to large artifacts that live outside git.

## Current Hardware

| id | hardware | role |
| --- | --- | --- |
| `orange-rk3588` | Orange Pi 5 Plus, RK3588, 16GB RAM | Primary multimodal deployment board and RK1828 host |
| RK1828 M.2 accelerator | RK1828 card attached to the RK3588 host | RKNN3 accelerator target; requires separate 12V before RK3588 boot; currently blocked by missing host RKEP kernel support |
| `linaro-rk3576` | RK3576, 8GB RAM | Main RK3576 validation board |
| `lckfb-rk3576` | RK3576, 4GB RAM | Low-memory RK3576 validation board |
| home server | Ubuntu machine with RTX 4060 Ti 8GB | Model download, LoRA/QLoRA, RKNN/RKLLM/RKNN3 conversion, packaging |

## Current Model State

RK3588 has a working `Qwen/Qwen3.5-4B` multimodal deployment and earlier Qwen3-VL/Qwen1.5 baselines.

RK3576 has working vendor-demo paths for `Qwen3-VL-2B-Instruct`, with `linaro-rk3576` preferred over the 4GB TaishanPi board.

RK1828 has completed RKNN3 conversion for `Qwen/Qwen3-VL-4B-Instruct` using RKNN3 Toolkit `1.0.4`. With RK1828 12V powered before RK3588 boot, the host detects the RK1828 PCIe endpoint as `0000:01:00.0`. Runtime validation is still blocked because the current Orange Pi RK3588 kernel lacks the Rockchip RKEP PCIe transfer driver path required by `rknn3_transfer_proxy`.

## Important Paths

Mac repo:

```text
/Users/wq/edge-model-lab
```

Home server repo/artifact root:

```text
/home/wq/edge-model-lab
```

RK1828 converted artifact bundle on the home server:

```text
/home/wq/edge-model-lab/models/artifacts/rk1828/qwen3-vl-4b
```

RK1828 conversion environment:

```text
/home/wq/edge-tools/rknn3-qwen3vl-py310
/home/wq/lincaigui/rknn3-model-zoo
/home/wq/edge-model-sources/huggingface/Qwen/Qwen3-VL-4B-Instruct
```

## Source Of Truth Rules

Use `models/assets.yaml` for model registry metadata.

Use `docs/experiments/` for chronological records of what happened.

Use `docs/guides/` for cleaned-up operating instructions.

Use `models/artifacts/**/manifest.yaml` for checksums, file sizes, and runtime bundle contents.

Do not commit large converted model files. The `.gitignore` intentionally ignores `models/artifacts/**` except small `README.md` and `manifest.yaml` files.

## RK1828 Caution

Do not mark RK1828 as working until the physical card is powered, detected by the RK3588 host, the host kernel exposes RKEP PCIe transfer support, and a runtime smoke test loads the RKNN3 artifacts successfully.

Conversion success means the home-server artifact build completed. It does not prove the host board, PCIe/M.2 link, runtime libraries, driver, power, or thermal setup is correct.

Known-good power order:

```text
RK1828 12V on first -> boot or reboot RK3588 -> lspci shows 0000:01:00.0
```

Current host-kernel blocker:

```text
Linux orangepi5plus 6.1.43-rockchip-rk3588 #1.0.8
# CONFIG_PCIE_FUNC_RKEP is not set
```
