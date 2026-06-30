# Edge Model Lab Project Handoff

## What This Project Is

`/Users/wq/edge-model-lab` is now the control project for deploying and validating edge-side AI models on three Rockchip boards.

The Mac is the control machine. The boards are remote deployment targets reached over SSH.

The project has four jobs:

1. Keep a stable inventory of the three devices.
2. Track model assets without copying huge model files into git.
3. Provide repeatable `edgectl` commands for deployment and smoke tests.
4. Preserve the hard-won deployment knowledge so the next board is faster.

## Current Devices

| project id | board | chip class | memory/storage | role |
| --- | --- | --- | --- | --- |
| `orange-rk3588` | Orange Pi 5 Plus | RK3588 | 16G/256G | primary multimodal LLM board |
| `linaro-rk3576` | KICKPI K7 | RK3576 | 8G/64G | main RK3576 validation board |
| `lckfb-rk3576` | TaishanPi | RK3576 | 4G/64G | low-memory validation board |

Inventory lives in:

- `devices.yaml`
- `inventory/reports/`
- `inventory/raw-logs/`

Local password overrides live in ignored `devices.local.yaml`.

## Current Model Deployment State

### Orange Pi RK3588

Status: successful Qwen3-VL-4B multimodal deployment.

Deployed board path:

```text
/home/orangepi/edge-model-lab/qwen3-vl-rk3588
```

Important deployed files:

```text
demo/demo
demo/imgenc
demo/lib/librkllmrt.so
demo/lib/librknnrt.so
models/qwen3-vl_vision_rk3588.rknn
models/qwen3-vl-4b-instruct_w8a8_rk3588.rkllm
```

Working smoke command:

```bash
EDGE_ORANGE_RK3588_PASSWORD='...' ./scripts/edgectl rk3588-qwen3-vl-smoke orange-rk3588
```

Known successful state:

```text
kernel: 6.1.43-rockchip-rk3588 #1.0.8
RKNPU driver: v0.9.8
CMA boot arg: cma=3584M
RKLLM runtime: 1.2.3
Qwen3-VL model: W8A8, max_context_limit=4096, npu_core_num=3
```

### K7 RK3576

Status: Qwen3-VL-2B RK3576 vendor demo can load and generate.

Working path:

```bash
EDGE_LINARO_RK3576_PASSWORD='...' ./scripts/edgectl llm-deploy linaro-rk3576
```

This board is the better RK3576 LLM target because it has 8G RAM.

### TaishanPi RK3576

Status: Qwen3-VL-2B deployment plumbing works, but generation is constrained by 4G RAM.

Working path:

```bash
EDGE_LCKFB_RK3576_PASSWORD='...' ./scripts/edgectl llm-deploy lckfb-rk3576
```

Use this board to validate low-memory behavior, not as the main LLM performance target.

## What Was Hard

The hard part was not one command. The work split into several layers:

1. Board inventory and SSH access.
2. Understanding which artifacts target RK3576 versus RK3588.
3. Converting Qwen3-VL-4B from Hugging Face to RK3588 RKLLM/RKNN artifacts.
4. Moving multi-gigabyte artifacts reliably.
5. Fixing the Orange Pi RKNPU driver and CMA memory setup.
6. Wrapping success into repeatable project commands.

The most important lesson: on Rockchip boards, a model can be correctly converted and still fail if the board kernel, RKNPU driver, device tree, runtime library, and CMA memory reservation do not line up.

## Key Local and Server Paths

Mac project:

```text
/Users/wq/edge-model-lab
```

Reference materials:

```text
/Users/wq/Documents/ZSPACE/sata11-15850752485/百度网盘下载/香橙派RK3588S
/Users/wq/Documents/ZSPACE/sata11-15850752485/百度网盘下载/K7 rk3576
/Users/wq/Documents/ZSPACE/sata11-15850752485/百度网盘下载/立创·泰山派RK3576开发板资料
```

Home server conversion workspace:

```text
/home/wq/edge-workspaces/rkllm-qwen3-vl-rk3588-v123
```

Home server source model:

```text
/home/wq/edge-model-sources/huggingface/Qwen/Qwen3-VL-4B-Instruct
```

RKLLM release used:

```text
/home/wq/edge-tools/rknn-llm-release-v1.2.3
```

## What To Do Next

Near-term improvements:

1. Replace the vendor interactive demo with a non-interactive wrapper so image questions do not loop on EOF.
2. Add a proper `edgectl rk3588-qwen3-vl-ask <image> <prompt>` command.
3. Add throughput and memory benchmark collection.
4. Convert this project into a one-command deployer for all three boards.
5. Preserve the working Orange Pi kernel package and rollback notes in a local artifact cache outside git.

Do not start by changing models. First make the current successful path easy to rerun and measure.
