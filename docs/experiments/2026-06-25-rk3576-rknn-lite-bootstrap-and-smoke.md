# RK3576 RKNN Lite Bootstrap And Smoke

Date: 2026-06-25

## Goal

Initialize the two RK3576 boards with a minimal Python RKNN Lite runtime and verify that each board can load and initialize a RK3576 RKNN model.

## Tooling Added

```bash
./scripts/edgectl rknn-bootstrap <device|all>
```

The command extracts the Python 3.11 aarch64 RKNN Lite wheel from the local K7 `rknn-toolkit2.zip`, uploads it to the target, creates `/home/<user>/edge-model-lab/venv`, installs `numpy`, `psutil`, `ruamel.yaml`, and `rknn-toolkit-lite2`, then verifies import and runtime library metadata.

The bootstrap is idempotent enough for this phase: if a previous failed run leaves a venv without `pip`, the venv is deleted and recreated.

## linaro-rk3576 Result

Bootstrap:

```text
rknnlite_import=ok
numpy 2.4.6
psutil 7.2.2
librknnrt version: 2.0.0b0 (35a6907d79@2024-03-24T10:31:14)
```

Smoke command:

```bash
EDGE_LINARO_RK3576_PASSWORD='...' ./scripts/edgectl rknn-smoke linaro-rk3576 rk3576_mobilenet_v2_lite2
```

Smoke result:

```text
load_ret=0
init_ret=0
elapsed_ms=155
librknnrt version: 2.0.0b0
driver version: 0.9.7
target platform: rk3576
```

## lckfb-rk3576 Result

Bootstrap:

```text
rknnlite_import=ok
numpy 2.4.6
psutil 7.2.2
librknnrt version: 2.3.0 (c949ad889d@2024-11-07T11:35:33)
```

Smoke command:

```bash
EDGE_LCKFB_RK3576_PASSWORD='...' ./scripts/edgectl rknn-smoke lckfb-rk3576 rk3576_mobilenet_v2_lite2
```

Smoke result:

```text
load_ret=0
init_ret=0
elapsed_ms=155
librknnrt version: 2.3.0
driver version: 0.9.8
target platform: rk3576
```

## Notes

- Both boards initially lacked `pip3` and a usable venv runtime.
- Installing `python3.11-venv`, `python3-venv`, and `python3-pip` upgraded Python 3.11 patch packages and caused transient SSH disconnects. Re-running bootstrap completed cleanly.
- Parallel RKNN smoke attempts triggered transient SSH disconnects on RK3576 boards; sequential single-device smoke runs succeeded. Treat this as a current automation constraint and avoid parallel SCP/SSH load until connection stability is improved.
- `linaro-rk3576` uses older runtime 2.0.0b0 while `lckfb-rk3576` uses 2.3.0. This should be normalized later if model compatibility issues appear.

## Status

All three boards now have a minimal RKNN Lite load/init smoke path:

- `orange-rk3588`: RK3588 model `load_ret=0`, `init_ret=0`
- `linaro-rk3576`: RK3576 model `load_ret=0`, `init_ret=0`
- `lckfb-rk3576`: RK3576 model `load_ret=0`, `init_ret=0`

## Next Steps

- Add benchmark mode that runs repeated `init_runtime()` and real inference loops with memory and temperature snapshots.
- Run K7 YOLOv5 RK3576 demo on `linaro-rk3576`.
- Normalize RKNN runtime versions or explicitly record per-device compatibility constraints.
