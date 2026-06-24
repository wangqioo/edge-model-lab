# Local Vendor Assets And RK3588 RKNN Smoke

Date: 2026-06-25

## Goal

Use the local board vendor data directories as project inputs, register useful model assets without copying large blobs into git, and run the first RK3588 RKNN Lite smoke test from a local vendor model.

## Source Data

- Orange Pi RK3588S data: `/Users/wq/Documents/ZSPACE/sata11-15850752485/百度网盘下载/香橙派RK3588S`
- K7 RK3576 data: `/Users/wq/Documents/ZSPACE/sata11-15850752485/百度网盘下载/K7 rk3576`
- LCKFB TaishanPi RK3576 data: `/Users/wq/Documents/ZSPACE/sata11-15850752485/百度网盘下载/立创·泰山派RK3576开发板资料`

## Registered Assets

`models/assets.yaml` now tracks the first usable project asset set:

- RK3588 Mobilenet V2 RKNN Lite example from `rknn-toolkit2.zip`
- RK3576 Mobilenet V2 RKNN Lite example from `rknn-toolkit2.zip`
- RK3588 ResNet18 RKNN Lite example from `rknn-toolkit2.zip`
- RK3576 ResNet18 RKNN Lite example from `rknn-toolkit2.zip`
- K7 RK3576 YOLOv5s demo model from `rknn_yolov5_demo_Linux_rk3576.zip`
- TaishanPi RK3576 Qwen3-VL vision `.rknn` and paired `.rkllm`
- TaishanPi YOLO11/YOLOv8 ONNX conversion sources

Large model files remain in the source data folders. The project stores paths, archive members, target platform, workload, and notes only.

## Tooling Added

```bash
./scripts/edgectl models --platform rk3588
./scripts/edgectl models --platform rk3576
./scripts/edgectl rknn-smoke <device> <asset> --python <target-python>
```

`rknn-smoke` extracts a registered `.rknn` asset if needed, uploads it to `/tmp/edge-model-lab-smoke` on the target, imports RKNN Lite, calls `load_rknn()`, and calls `init_runtime()`.

## RK3588 Smoke Result

Command:

```bash
EDGE_ORANGE_RK3588_PASSWORD='...' ./scripts/edgectl rknn-smoke orange-rk3588 rk3588_mobilenet_v2_lite2
```

Result:

```text
load_ret=0
init_ret=0
elapsed_ms=69
librknnrt version: 2.3.2 (429f97ae6b@2025-04-09T09:09:27)
driver version: 0.9.6
target platform: rk3588
model inference type: dynamic_shape
```

This proves the Orange Pi RK3588 board can load and initialize a RK3588 RKNN model through RKNN Lite using the remediated runtime stack.

## Next Steps

- Install the same minimal Python/RKNN Lite runtime on `linaro-rk3576` and `lckfb-rk3576`.
- Run `rk3576_mobilenet_v2_lite2` on both RK3576 boards.
- Run the K7 RK3576 YOLOv5 binary demo on `linaro-rk3576`.
- Convert or obtain a detection model for RK3588 so the three-board baseline uses comparable workloads.
