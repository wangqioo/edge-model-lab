# Edge Model Lab Milestones

## M1: Project Foundation

- Preserve reports and raw logs.
- Create device inventory.
- Implement `edgectl list`.
- Implement read-only `edgectl health`.

## M2: RK3588 Baseline

- Harden SSH on `orange-rk3588`.
- [x] Resolve built-in RKNN demo runtime libraries.
- [x] Prefer a headless RKNN Lite demo over the built-in MiniGUI camera-preview demo.
- [x] Generate or obtain a RK3588-compatible RKNN model artifact.
- [x] Verify RKNN Lite can load and initialize a RK3588 model on the board.
- Record first latency, memory, and temperature baseline.
- Decide Docker device mappings for RKNN/RGA/Mali access.

## M3: Python Runtime Baseline

- Define common Python venv layout.
- [x] Define common Python venv layout.
- [x] Install minimal runtime packages on each board.
- [x] Verify RKNN Lite import and RKNN runtime initialization on all three boards.
- Record runtime package versions.

## M4: RK3576 Systemd Service

- Create a minimal Python inference service.
- Deploy via systemd on `linaro-rk3576`.
- Repeat on `lckfb-rk3576`.
- Record memory and thermal behavior.

## M5: RK3588 Docker Compose Service

- Package the minimal inference service in a Docker image.
- Deploy with Docker Compose on `orange-rk3588`.
- Verify NPU/RGA/GPU access from inside the container.

## M6: Benchmarks And Regression Checks

- Add benchmark result format.
- Capture latency, throughput, memory, disk, and temperature.
- Add repeatable smoke tests for all three boards.
