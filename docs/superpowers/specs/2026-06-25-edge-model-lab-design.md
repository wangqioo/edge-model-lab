# Edge Model Lab Design

## Summary

Build `/Users/wq/edge-model-lab` as a long-running project for edge-side model deployment validation across three Rockchip boards. It begins as an inventory and control-script repository and evolves into a one-command deployment tool.

## Approved Direction

The project should become a future one-click deployment tool for all three devices, but the first phase should stay small and reliable.

The local Mac is the control machine. The boards are target devices accessed over SSH.

## Device Roles

- `orange-rk3588`: primary deployment target, Docker-first, best for multi-service and model deployment experiments.
- `linaro-rk3576`: main RK3576 compatibility target, systemd plus Python venv first.
- `lckfb-rk3576`: low-memory validation target for minimum viable runtime tests.

## Repository Structure

```text
README.md
devices.yaml
inventory/reports/
inventory/raw-logs/
docs/
docs/experiments/
scripts/
scripts/lib/
deploy/systemd/
deploy/compose/
models/
benchmarks/
```

## Phase 1 Requirements

- Preserve the three audit reports and raw logs.
- Add a machine-readable `devices.yaml`.
- Keep secrets out of versioned files.
- Implement `./scripts/edgectl list`.
- Implement `./scripts/edgectl health all`.
- Implement `./scripts/edgectl health <device-id>`.
- Health checks are read-only.

## Health Check Data

Health checks should report:

- SSH reachability.
- Hostname, OS, kernel, uptime.
- Memory and storage usage.
- Thermal zones.
- Docker/containerd availability.
- Python/pip availability.
- RKNN runtime/demo file presence.
- NPU/RGA/Mali device and sysfs presence.
- Failed systemd units.

## Non-Goals

- No dashboard in phase 1.
- No automatic package install in phase 1.
- No model conversion pipeline in phase 1.
- No password storage in `devices.yaml`.
- No destructive target-device operations.

## Open Design Defaults

- Use YAML for inventory.
- Use a local CLI script as the control interface.
- Prefer SSH keys.
- Allow password fallback only through ignored local config or environment variables.

