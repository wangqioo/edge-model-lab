# RK3576 systemd Deployment Skeleton

This directory contains the first systemd shape for RK3576 inference workloads.

Target layout:

```text
/opt/edge/
  apps/
  models/
  logs/
  run/
```

Current units:

- `edge-rknn-yolo-smoke.service`: one-shot smoke unit for the vendor YOLOv5 demo.
- `edge-rknn-python.service`: long-running local HTTP service for Python RKNN inference validation.

YOLO deployment steps:

1. Copy the validated app bundle to `/opt/edge/apps/rknn_yolov5_demo`.
2. Keep model blobs under `/opt/edge/models` when they are no longer packaged with the app.
3. Install the unit to `/etc/systemd/system/edge-rknn-yolo-smoke.service`.
4. Run `systemctl daemon-reload`.
5. Use `systemctl start edge-rknn-yolo-smoke.service` for a one-shot smoke run.

Python service deployment steps:

1. Copy `deploy/apps/rknn_service/edge_rknn_service.py` to `/opt/edge/apps/rknn_service`.
2. Copy `rk3576_resnet18_lite2.rknn` to `/opt/edge/models`.
3. Render `edge-rknn-python.service` with the target user's Python venv path and user name.
4. Run `systemctl daemon-reload`.
5. Restart `edge-rknn-python.service`.
6. Check `http://127.0.0.1:18080/health` and `http://127.0.0.1:18080/infer/synthetic` from the device.

The `edgectl rknn-service-deploy <device>` command performs those Python service steps for RK3576 targets.
