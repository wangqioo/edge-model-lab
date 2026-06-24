# Edge Model Lab Project Design

## Purpose

Edge Model Lab turns three Rockchip boards into a managed validation project for edge-side model deployment. The project starts as a reliable inventory and control-script repository, then grows into a repeatable deployment tool.

The control machine is the local Mac. The target devices are accessed over SSH.

## Device Roles

`orange-rk3588` is the primary deployment target. It has the most memory and storage, Docker/containerd are already installed, and RKNN runtime/demo files are present. It should be the first board used to validate RKNN demo inference and Docker Compose deployment.

`linaro-rk3576` is the main RK3576 validation board. It has enough memory for stable Python inference service testing and should use systemd plus a Python virtual environment first.

`lckfb-rk3576` is the low-memory validation board. It should validate the smallest deployable runtime and resource limits for RK3576-class hardware.

## Architecture

The project uses a local command-line controller, `scripts/edgectl`, backed by `devices.yaml`.

The first implementation should keep behavior simple:

- Read device inventory from `devices.yaml`.
- Never store passwords in the main project config.
- Connect over SSH using keys or optional local credential overrides.
- Print human-readable health reports first; machine-readable JSON can be added later.
- Treat device changes as explicit future actions. Health checks must be read-only.

## Deployment Backends

The project tracks two deployment backends:

- `docker`: used first on `orange-rk3588`.
- `systemd-venv`: used first on both RK3576 boards.

The backend choice is a default, not a permanent limitation. RK3576 Docker support can be added after the basic systemd path is stable.

## Phase 1 Scope

Phase 1 creates the foundation:

- Preserve the existing reports and raw logs.
- Add `devices.yaml`.
- Add `scripts/edgectl list`.
- Add `scripts/edgectl health <device|all>`.
- Document milestones and experiment workflow.

Health checks should collect:

- SSH reachability.
- Hostname, OS, kernel, uptime.
- Memory, storage, and thermal status.
- Docker/containerd presence.
- Python and pip presence.
- RKNN runtime/demo file presence.
- NPU/RGA/Mali device/sysfs presence.
- Failed systemd units.

## Non-Goals For Phase 1

- No web dashboard.
- No model conversion pipeline.
- No automatic package installation.
- No password storage in `devices.yaml`.
- No destructive cleanup on target devices.

## Security Model

SSH keys are preferred. Password access can be used temporarily through environment variables or `devices.local.yaml`, which is ignored by git.

The Orange Pi target was observed to allow root password login. Hardening that host is an early project task before it is used as a long-running deployment node.

