# Edge Model Lab

Edge Model Lab is the control project for validating and deploying edge-side model workloads on three Rockchip devices.

The Mac at `/Users/wq` is the control machine. The boards are deployment targets:

- `orange-rk3588`: Orange Pi RK3588 / 16G+256G, primary deployment target, Docker-first.
- `linaro-rk3576`: RK3576 / 8G+64G, main RK3576 compatibility target, systemd + Python venv first.
- `lckfb-rk3576`: RK3576 / 4G+64G, low-memory validation target.

## Current Phase

Phase 1 foundation is in place, and Phase 2 RK3588 baseline is underway:

- Preserve device audit reports and raw logs.
- Maintain a machine-readable device inventory.
- Build a local `edgectl` command for listing and health-checking devices.
- Register local vendor RKNN/RKLLM/ONNX assets without committing large model blobs.
- Run minimum RKNN Lite smoke tests on target boards.
- Keep passwords and secrets out of the project.

## Layout

```text
inventory/reports/   Human-readable device reports.
inventory/raw-logs/  Raw audit command output.
docs/                Project design, milestones, experiment notes.
scripts/             Local control scripts.
deploy/              Future systemd and Docker Compose deployment files.
models/              Model metadata and conversion notes, not large model blobs.
benchmarks/          Benchmark plans and results.
```

## First Commands

Planned phase 1 interface:

```bash
./scripts/edgectl list
./scripts/edgectl health all
./scripts/edgectl health orange-rk3588
./scripts/edgectl models --platform rk3588
./scripts/edgectl rknn-bootstrap linaro-rk3576
./scripts/edgectl rknn-smoke orange-rk3588 rk3588_mobilenet_v2_lite2
```

`models/assets.yaml` stores metadata and local source paths for vendor assets. Large `.rknn`, `.rkllm`, `.onnx`, and `.pt` files stay in the original data directories.

## Security

`devices.yaml` intentionally does not store passwords. Use SSH keys, environment variables, or an ignored local credential file for access.

## Local Credential Setup

Preferred setup is SSH key auth to each board.

For temporary password auth:

```bash
cp devices.local.example.yaml devices.local.yaml
export EDGE_ORANGE_RK3588_PASSWORD='...'
export EDGE_LINARO_RK3576_PASSWORD='...'
export EDGE_LCKFB_RK3576_PASSWORD='...'
```

`devices.local.yaml` is ignored by git.
