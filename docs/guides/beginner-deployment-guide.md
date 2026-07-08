# Beginner Deployment Guide

This guide assumes you are new to edge model deployment on Rockchip chips.

## The Mental Model

A normal cloud model deployment usually has:

```text
model weights -> Python runtime -> GPU/CPU
```

A Rockchip edge deployment has more moving parts:

```text
source model
  -> conversion toolkit
  -> chip-specific model file
  -> runtime library
  -> kernel driver
  -> NPU memory reservation
  -> board demo/service
```

If any layer is wrong, the model can fail even if the model file itself is correct.

## Important Terms

### NPU

The neural processing unit on the Rockchip SoC. It is the accelerator that runs converted model graphs.

### RKNPU

The Rockchip NPU kernel driver. User-space runtimes talk to this driver.

For the successful Orange Pi Qwen3-VL-4B deployment, the critical fix was upgrading RKNPU from `0.9.6` to `0.9.8`.

### RKNN

Rockchip's NPU model format, commonly used for vision models.

Example:

```text
qwen3-vl_vision_rk3588.rknn
```

### RKLLM

Rockchip's LLM model format/runtime path.

Example:

```text
qwen3-vl-4b-instruct_w8a8_rk3588.rkllm
```

### RKNN Toolkit / RKLLM Toolkit

Conversion tools that run on a host machine, usually Linux x86_64. They take a source model and export Rockchip-specific artifacts.

The Qwen3-VL-4B conversion used RKLLM `1.2.3`, not the older `1.1.4` package in the Orange Pi material.

### Runtime Library

The board-side `.so` file used by the executable.

Common files:

```text
librknnrt.so
librkllmrt.so
```

The conversion toolkit version and runtime library version should match closely.

### CMA

Contiguous Memory Allocator. Large NPU allocations often need physically contiguous memory.

For the Orange Pi:

```text
extraargs=cma=3584M
```

This is set in:

```text
/boot/orangepiEnv.txt
```

### Quantization

A way to reduce model size and make inference cheaper. This project primarily used `W8A8`.

The successful Qwen3-VL-4B RKLLM is:

```text
model_dtype: W8A8
max_context_limit: 4096
npu_core_num: 3
```

## The Deployment Workflow

### Step 1: Identify the Chip

Do not mix artifacts across chips.

RK3576 artifacts should not be deployed directly onto RK3588, and RK3588 artifacts should not be assumed to work on RK3576.

Use:

```bash
./scripts/edgectl list
./scripts/edgectl health orange-rk3588
```

### Step 2: Confirm the Model Format

For vision/classification/object detection:

```text
.rknn
```

For LLM text or multimodal LLM language side:

```text
.rkllm
```

For source models:

```text
Hugging Face directory, .safetensors, .onnx
```

### Step 3: Use the Right Conversion Host

Do not convert Qwen3-VL-4B on the Mac. The RKLLM wheel is Linux x86_64 and the model is large.

Use the home Linux server:

```text
wq@192.168.1.39
```

The Qwen3-VL workspace is:

```text
/home/wq/edge-workspaces/rkllm-qwen3-vl-rk3588-v123
```

### Step 4: Build or Collect Artifacts

For Qwen3-VL multimodal deployment, there are two model artifacts:

```text
qwen3-vl_vision_rk3588.rknn
qwen3-vl-4b-instruct_w8a8_rk3588.rkllm
```

The vision side and language side are separate. Both must match the target chip.

### Step 5: Deploy to the Board

Large files should use chunked upload or size-checked upload. Direct `scp` can silently truncate on unstable links.

The project already has helper code for chunked upload in:

```text
scripts/lib/ssh.py
```

### Step 6: Verify the Board Runtime

Check:

```bash
uname -a
sudo cat /sys/kernel/debug/rknpu/version
grep -E "CmaTotal|CmaFree" /proc/meminfo
```

For Orange Pi Qwen3-VL-4B, expected:

```text
RKNPU driver: v0.9.8
CmaTotal: 3670016 kB
```

### Step 7: Smoke Test

Use project commands instead of one-off commands where possible:

```bash
EDGE_ORANGE_RK3588_PASSWORD='...' ./scripts/edgectl rk3588-qwen3-vl-smoke orange-rk3588
```

Expected evidence:

```text
rkllm init success
robot:
```

## What Went Wrong This Time

The Qwen3-VL-4B model artifacts were eventually correct, but the Orange Pi failed with:

```text
failed to malloc npu memory
rknpu driver version: 0.9.6
```

Increasing CMA helped expose the limit but did not fully solve it. The decisive fix was upgrading the kernel package so RKNPU became `v0.9.8`.

After the upgrade, the same original `ctx4096/core3` RKLLM loaded successfully.

## Practical Rules

1. Never trust "file exists" as proof of deployment. Run the model.
2. Never trust "model converted" as proof it will load. Check driver and CMA.
3. Keep source model, conversion workspace, deployment path, and board runtime versions documented.
4. Prefer repeatable smoke commands over copied shell history.
5. When changing kernels or boot args, keep a rollback copy of `/boot`.
