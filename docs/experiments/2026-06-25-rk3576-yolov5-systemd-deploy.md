# RK3576 YOLOv5 systemd Deploy

Date: 2026-06-25

## Goal

Promote the RK3576 YOLOv5 vendor demo from `/tmp` smoke execution to a fixed `/opt/edge` deployment path managed by a systemd one-shot service.

## Tooling Added

```bash
./scripts/edgectl yolo-deploy <device>
```

The command:

- uploads or reuses the K7 RK3576 YOLOv5 demo files,
- creates the `edge` system user if missing,
- adds `edge` to `video` and `render`,
- installs the app under `/opt/edge/apps/rknn_yolov5_demo`,
- installs `/etc/systemd/system/edge-rknn-yolo-smoke.service`,
- runs `systemctl daemon-reload`,
- starts the one-shot service,
- prints `systemctl status`.

## Permission Finding

The first systemd attempt failed on `linaro-rk3576`:

```text
failed to open rknpu module, need to insmod rknpu dirver
failed to open rknn device
rknn_init error ret=-1
```

Root cause: the `edge` service user did not have the same device access groups as the interactive board user. The fix was:

- add `edge` to `video` and `render`,
- add `SupplementaryGroups=video render` to the unit.

## linaro-rk3576 Result

Command:

```bash
EDGE_LINARO_RK3576_PASSWORD='...' ./scripts/edgectl yolo-deploy linaro-rk3576
```

Result:

```text
Active: active (exited)
ExecStart status=0/SUCCESS
once run use 46.040000 ms
loop count = 10 , average run  43.031300 ms
```

Detected objects:

```text
person @ (209 243 286 510) 0.879723
person @ (479 238 560 526) 0.870588
person @ (109 237 232 534) 0.828112
bus @ (93 129 553 464) 0.700761
person @ (79 353 122 517) 0.307297
```

## lckfb-rk3576 Result

Command:

```bash
EDGE_LCKFB_RK3576_PASSWORD='...' ./scripts/edgectl yolo-deploy lckfb-rk3576
```

Result:

```text
Active: active (exited)
ExecStart status=0/SUCCESS
once run use 49.281000 ms
loop count = 10 , average run  23.603700 ms
```

Detected objects:

```text
person @ (209 243 286 510) 0.879723
person @ (479 238 560 526) 0.870588
person @ (109 237 232 534) 0.828112
bus @ (93 129 553 464) 0.700761
person @ (79 353 122 517) 0.307297
```

## Status

Both RK3576 boards can now run the YOLOv5 vendor demo through systemd from the fixed `/opt/edge` layout.

## Next Steps

- Add `edgectl service-status <device>` and `edgectl logs <device> <unit>` helpers.
- Convert this one-shot service into a long-running Python inference service.
- Add a benchmark command that records governor, NPU frequency, temperature, memory, and repeated latency.
