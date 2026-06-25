# RK3576 YOLO Smoke And Systemd Skeleton Design

## Goal

Add a repeatable RK3576 YOLOv5 validation path and the first systemd deployment skeleton for future RK3576 inference services.

## Scope

This phase does three things:

- Runs the K7 vendor YOLOv5 RK3576 demo on `linaro-rk3576`.
- Adds an `edgectl yolo-smoke <device>` command that extracts, uploads, and executes the demo.
- Adds systemd skeleton files and directory conventions for RK3576 services without starting a persistent service yet.

This phase does not build a custom inference server, convert models, or normalize RKNN runtime versions.

## Architecture

`edgectl yolo-smoke` will use the existing SSH/SCP helpers and the local K7 demo archive:

`/Users/wq/Documents/ZSPACE/sata11-15850752485/百度网盘下载/K7 rk3576/3-SoftwareData/Linux_rknn_yolov5/rknn_yolov5_demo_Linux_rk3576.zip`

The command will extract the archive locally to a temporary directory, upload the extracted demo directory to `/tmp/edge-model-lab-yolo/<asset-id>` on the target, mark binaries executable, and run the image demo with `LD_LIBRARY_PATH` pointed at the demo `lib` directory.

The command will reject non-RK3576 devices because the bundled model is RK3576-specific.

## Components

- `scripts/lib/yolo.py`: K7 YOLOv5 archive extraction, upload, remote execution, and output printing.
- `scripts/lib/cli.py`: Adds `yolo-smoke`.
- `deploy/systemd/rk3576/edge-rknn-yolo-smoke.service`: Template-like service unit for future one-shot smoke execution.
- `deploy/systemd/rk3576/README.md`: Directory layout and deployment notes.
- `docs/experiments/2026-06-25-rk3576-yolov5-demo-smoke.md`: Captures command output, errors, runtime versions, and next steps.

## Remote Layout

Temporary smoke deployment:

```text
/tmp/edge-model-lab-yolo/k7_rk3576_yolov5s_demo/
  rknn_yolov5_demo
  rknn_yolov5_video_demo
  lib/
  model/
```

Future persistent deployment convention:

```text
/opt/edge/
  apps/
  models/
  logs/
  run/
```

## Error Handling

- If the device is not RK3576, fail before upload.
- If archive extraction fails, print the extractor error and return non-zero.
- If SSH/SCP fails, print the remote transport error and return non-zero.
- If the demo exits non-zero, print stdout/stderr and return the remote exit code.
- Run RK3576 smoke commands sequentially; previous work showed parallel SSH/SCP can trigger transient disconnects.

## Testing

- Run `python3 -m compileall scripts`.
- Run `./scripts/edgectl yolo-smoke linaro-rk3576`.
- If successful on `linaro-rk3576`, optionally run `./scripts/edgectl yolo-smoke lckfb-rk3576` as a low-memory check.
- Record actual output in the experiment document.

## Spec Review

- No placeholders remain.
- Scope is intentionally limited to vendor demo execution and systemd skeleton.
- The command is device-scoped and does not mutate persistent service state.
