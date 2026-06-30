# Command Reference

Run commands from:

```bash
cd /Users/wq/edge-model-lab
```

## Credentials

Temporary password environment variables:

```bash
export EDGE_ORANGE_RK3588_PASSWORD='...'
export EDGE_LINARO_RK3576_PASSWORD='...'
export EDGE_LCKFB_RK3576_PASSWORD='...'
```

Preferred long-term setup is SSH keys and no password variables.

## Inventory

List boards:

```bash
./scripts/edgectl list
```

Health check all boards:

```bash
./scripts/edgectl health all
```

Health check one board:

```bash
./scripts/edgectl health orange-rk3588
```

List model metadata:

```bash
./scripts/edgectl models
./scripts/edgectl models --platform rk3588
./scripts/edgectl models --platform rk3576
```

## RK3588 Qwen3-VL-4B

Smoke test deployed model:

```bash
EDGE_ORANGE_RK3588_PASSWORD='...' ./scripts/edgectl rk3588-qwen3-vl-smoke orange-rk3588
```

Manual board checks:

```bash
sshpass -p "$EDGE_ORANGE_RK3588_PASSWORD" ssh -o StrictHostKeyChecking=no orangepi@192.168.1.52 '
uname -a
printf "%s\n" "$EDGE_ORANGE_RK3588_PASSWORD" | sudo -S -p "" cat /sys/kernel/debug/rknpu/version
grep -E "CmaTotal|CmaFree" /proc/meminfo
'
```

Clean stuck demo:

```bash
sshpass -p "$EDGE_ORANGE_RK3588_PASSWORD" ssh -o StrictHostKeyChecking=no orangepi@192.168.1.52 '
printf "%s\n" "$EDGE_ORANGE_RK3588_PASSWORD" | sudo -S -p "" pkill -x demo 2>/dev/null || true
printf "%s\n" "$EDGE_ORANGE_RK3588_PASSWORD" | sudo -S -p "" pkill -x timeout 2>/dev/null || true
'
```

## RK3576 Qwen3-VL-2B

Deploy/smoke on K7:

```bash
EDGE_LINARO_RK3576_PASSWORD='...' ./scripts/edgectl llm-deploy linaro-rk3576
```

Deploy/smoke on TaishanPi:

```bash
EDGE_LCKFB_RK3576_PASSWORD='...' ./scripts/edgectl llm-deploy lckfb-rk3576
```

## RKNN Service

Deploy Python RKNN service:

```bash
./scripts/edgectl rknn-service-deploy linaro-rk3576
./scripts/edgectl rknn-service-deploy lckfb-rk3576
```

Benchmark:

```bash
./scripts/edgectl rknn-service-bench linaro-rk3576 --count 20
```

Systemd status:

```bash
./scripts/edgectl service-status linaro-rk3576 edge-rknn-python.service
./scripts/edgectl logs linaro-rk3576 edge-rknn-python.service --lines 80
```

## YOLO RK3576

Smoke:

```bash
./scripts/edgectl yolo-smoke linaro-rk3576
```

Deploy:

```bash
./scripts/edgectl yolo-deploy linaro-rk3576
```

## Conversion Helpers

Check local conversion materials:

```bash
./scripts/edgectl rkllm-conversion-check
```

Prepare Qwen3-VL conversion workspace:

```bash
./scripts/edgectl rkllm-prepare-conversion /path/to/large-linux-disk/rkllm-qwen3-vl
```

Download Hugging Face source model:

```bash
./scripts/edgectl rkllm-download-qwen3-vl-source --chunk-mb 32 --workers 4
```

## Local Verification

Run project tests:

```bash
python3 -m compileall scripts tests
python3 -m unittest tests/test_deploy.py
python3 -m unittest tests/test_rknn_service.py
```

## Git Hygiene

Check current worktree:

```bash
git status --short
```

Large model files should not be committed. Keep them in the original data directories or server workspace.
