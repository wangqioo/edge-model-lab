# RK3588 Qwen3-VL-4B Runbook

This is the repeatable runbook for the Orange Pi RK3588 Qwen3-VL-4B deployment.

## Current Result

The Orange Pi RK3588 board can run `Qwen3-VL-4B-Instruct` as a multimodal image-question-answering model.

Known working board state:

```text
board: Orange Pi 5 Plus
kernel: 6.1.43-rockchip-rk3588 #1.0.8
RKNPU: v0.9.8
CMA: cma=3584M
RKLLM runtime: 1.2.3
```

Known working deployed model:

```text
/home/orangepi/edge-model-lab/qwen3-vl-rk3588/models/qwen3-vl-4b-instruct_w8a8_rk3588.rkllm
/home/orangepi/edge-model-lab/qwen3-vl-rk3588/models/qwen3-vl_vision_rk3588.rknn
```

## Quick Smoke Test

From the Mac:

```bash
cd /Users/wq/edge-model-lab
EDGE_ORANGE_RK3588_PASSWORD='...' ./scripts/edgectl rk3588-qwen3-vl-smoke orange-rk3588
```

Success means the output includes:

```text
RKNPU driver: v0.9.8
rkllm init success
robot:
```

## Run a Custom Image Manually

Copy an image to the board:

```bash
sshpass -p "$EDGE_ORANGE_RK3588_PASSWORD" scp -o StrictHostKeyChecking=no \
  /Users/wq/Desktop/111.jpg \
  orangepi@192.168.1.52:/home/orangepi/edge-model-lab/qwen3-vl-rk3588/demo/user_111.jpg
```

Run the model:

```bash
sshpass -p "$EDGE_ORANGE_RK3588_PASSWORD" ssh -o StrictHostKeyChecking=no orangepi@192.168.1.52 '
cd /home/orangepi/edge-model-lab/qwen3-vl-rk3588/demo
printf "<image>请详细描述这张图片。\\n" |
  LD_LIBRARY_PATH=./lib timeout 110 ./demo \
    user_111.jpg \
    ../models/qwen3-vl_vision_rk3588.rknn \
    ../models/qwen3-vl-4b-instruct_w8a8_rk3588.rkllm \
    160 4096 3 \
    "<|vision_start|>" "<|vision_end|>" "<|image_pad|>"
'
```

Clean up the interactive demo if needed:

```bash
sshpass -p "$EDGE_ORANGE_RK3588_PASSWORD" ssh -o StrictHostKeyChecking=no orangepi@192.168.1.52 '
printf "%s\n" "$EDGE_ORANGE_RK3588_PASSWORD" | sudo -S -p "" pkill -x demo 2>/dev/null || true
printf "%s\n" "$EDGE_ORANGE_RK3588_PASSWORD" | sudo -S -p "" pkill -x timeout 2>/dev/null || true
'
```

The current vendor demo treats EOF as repeated empty prompts. This is why the smoke command uses `timeout` and validates output instead of requiring a graceful demo exit.

## Conversion Summary

Conversion ran on the home Linux server because the Mac is not the right host for RKLLM conversion.

Server workspace:

```text
/home/wq/edge-workspaces/rkllm-qwen3-vl-rk3588-v123
```

Source model:

```text
/home/wq/edge-model-sources/huggingface/Qwen/Qwen3-VL-4B-Instruct
```

RKLLM release:

```text
/home/wq/edge-tools/rknn-llm-release-v1.2.3
```

Python environments:

```text
/home/wq/edge-tools/rkllm123-py310
/home/wq/edge-tools/qwen3vl-vision-py310
/home/wq/edge-tools/rkllm-py310
```

Final artifacts:

| artifact | size | sha256 |
| --- | ---: | --- |
| `qwen3-vl-4b-instruct_w8a8_rk3588.rkllm` | `4,846,784,612` | `e4c5b2632a43ae5836abb3cde9686c6b20faefc02e378a560d6cbacaa2b362f1` |
| `qwen3-vl_vision_rk3588.rknn` | `869,260,061` | `20fd4b06a0b69c22c25fb71a61b4ae5f47d0ab4c7b273198522fc4c0ab220299` |

## Board Upgrade Summary

Before upgrade:

```text
kernel: 6.1.43-rockchip-rk3588 #1.2.0
RKNPU reported by RKLLM: 0.9.6
failure: failed to malloc npu memory
```

After upgrade:

```text
kernel: 6.1.43-rockchip-rk3588 #1.0.8
RKNPU: v0.9.8
result: Qwen3-VL-4B loads and answers image questions
```

Backup before upgrade:

```text
/home/orangepi/boot-backup-before-rknpu-upgrade-20260630-203252
```

Upgrade package:

```text
linux-image-current-rockchip-rk3588_1.0.8_arm64.deb
sha256: 325ecd331e51627c99e96ad8504f71913fd6cc82411f7fcf443697601fe66b0a
source: https://github.com/cse-repon/orangepi-5b-rknpu-0.9.8-update
```

Post-upgrade package state:

```text
linux-image-current-rockchip-rk3588 1.0.8
linux-dtb-current-rockchip-rk3588 1.2.0
```

## What Not To Change Casually

Do not casually change these without a rollback plan:

```text
/boot/Image
/boot/vmlinuz-6.1.43-rockchip-rk3588
/boot/orangepiEnv.txt
/lib/modules/6.1.43-rockchip-rk3588
```

Do not lower CMA if you want Qwen3-VL-4B to keep working.

Do not replace `librkllmrt.so` with an older runtime.

Do not replace the RK3588 `.rkllm` with a RK3576 `.rkllm`.

## Known Limitation

The deployed demo is not yet a polished service. It is an interactive vendor demo wrapped by scripts.

The next engineering step should be a stable non-interactive wrapper:

```text
image path + prompt -> one answer -> process exits
```

That wrapper should become:

```bash
./scripts/edgectl rk3588-qwen3-vl-ask orange-rk3588 /path/to/image.jpg "问题"
```
