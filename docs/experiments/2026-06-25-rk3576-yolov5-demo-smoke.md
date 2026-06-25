# RK3576 YOLOv5 Vendor Demo Smoke

Date: 2026-06-25

## Goal

Run the K7 RK3576 YOLOv5 vendor demo on both RK3576 boards and add a repeatable `edgectl yolo-smoke` command.

## Tooling Added

```bash
./scripts/edgectl yolo-smoke <device>
```

The command extracts the local K7 demo archive, uploads the demo files to:

```text
/tmp/edge-model-lab-yolo/k7_rk3576_yolov5s_demo
```

Then it runs:

```bash
LD_LIBRARY_PATH=./lib ./rknn_yolov5_demo model/RK3576/yolov5s-640-640.rknn model/bus.jpg
```

The command is RK3576-only.

## linaro-rk3576 Result

Command:

```bash
EDGE_LINARO_RK3576_PASSWORD='...' ./scripts/edgectl yolo-smoke linaro-rk3576
```

Result:

```text
sdk version: 2.0.0b0
driver version: 0.9.7
first successful run: once 62.351000 ms, average 54.304400 ms
verification run: once 60.291000 ms, average 45.939900 ms
person @ (209 243 286 510) 0.879723
person @ (479 238 560 526) 0.870588
person @ (109 237 232 534) 0.828112
bus @ (93 129 553 464) 0.700761
person @ (79 353 122 517) 0.307297
```

## lckfb-rk3576 Result

Command:

```bash
EDGE_LCKFB_RK3576_PASSWORD='...' ./scripts/edgectl yolo-smoke lckfb-rk3576
```

Result:

```text
sdk version: 2.0.0b0
driver version: 0.9.8
first successful run: once 51.175000 ms, average 23.713700 ms
verification run: once 53.850000 ms, average 39.703900 ms
person @ (209 243 286 510) 0.879723
person @ (479 238 560 526) 0.870588
person @ (109 237 232 534) 0.828112
bus @ (93 129 553 464) 0.700761
person @ (79 353 122 517) 0.307297
```

## Notes

- Both boards produced identical detections on `bus.jpg`.
- The demo uses its bundled `lib/librknnrt.so`, version `2.0.0b0`, instead of the board system runtime.
- `lckfb-rk3576` does not have remote `rsync`, so `edgectl yolo-smoke` falls back to individual SCP uploads.
- `lckfb-rk3576` initially dropped the large transfer; the per-file upload fallback completed successfully.
- The latency difference between the two RK3576 boards should not be treated as a final performance comparison yet. Governor state, thermal state, runtime version, and driver version need controlled benchmarking.

## Systemd Skeleton

Added:

```text
deploy/systemd/rk3576/README.md
deploy/systemd/rk3576/edge-rknn-yolo-smoke.service
```

The service is a one-shot skeleton for future persistent deployment under `/opt/edge`. It is not installed or enabled in this experiment.

## Next Steps

- Add a benchmark command that collects CPU governor, NPU frequency, temperature, memory, and repeated latency samples.
- Promote the YOLO demo from `/tmp` to `/opt/edge/apps/rknn_yolov5_demo` when we are ready to test systemd-managed deployment.
- Build a Python inference service around a known RKNN model after the binary demo path is stable.
