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

The current unit is a one-shot smoke skeleton for the vendor YOLOv5 demo. This phase does not install, enable, or start the service automatically.

Future deployment steps should:

1. Copy the validated app bundle to `/opt/edge/apps/rknn_yolov5_demo`.
2. Keep model blobs under `/opt/edge/models` when they are no longer packaged with the app.
3. Install the unit to `/etc/systemd/system/edge-rknn-yolo-smoke.service`.
4. Run `systemctl daemon-reload`.
5. Use `systemctl start edge-rknn-yolo-smoke.service` for a one-shot smoke run.
