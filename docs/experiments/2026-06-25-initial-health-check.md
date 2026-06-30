# Initial Health Check

## Goal

Verify the first `edgectl health all` implementation against all three target boards.

## Target Devices

- `orange-rk3588`
- `linaro-rk3576`
- `lckfb-rk3576`

## Command

```bash
EDGE_ORANGE_RK3588_PASSWORD='...' \
EDGE_LINARO_RK3576_PASSWORD='...' \
EDGE_LCKFB_RK3576_PASSWORD='...' \
./scripts/edgectl health all > /tmp/edge-model-lab-health.txt 2>&1
```

## Result

The command exited with status 0 after fixing SSH script transport to use `sh -s` with stdin.

Key observations:

- `orange-rk3588` reports Docker 27.3.1, containerd 1.7.23, Python 3.11.2, pip 23.0.1, RKNN demo/runtime libraries, Mali/RGA/dma_heap devices, and one failed unit: `smartmontools.service`.
- `linaro-rk3576` reports Python 3.11.2, RKNN server/runtime library, Mali/RGA/dma_heap devices, no Docker/containerd, no pip3, and one failed unit: `console-setup.service`.
- `lckfb-rk3576` reports Python 3.11.2, RKNN server/runtime library, Mali/RGA/dma_heap devices, no Docker/containerd, no pip3, and no failed units.

## Follow-Up Actions

- Add SSH key auth to avoid password environment variables.
- Harden `orange-rk3588` root password login before long-running deployments.
- Create the RK3588 RKNN demo baseline task.
- Define the Python venv package baseline for RK3576 devices.

