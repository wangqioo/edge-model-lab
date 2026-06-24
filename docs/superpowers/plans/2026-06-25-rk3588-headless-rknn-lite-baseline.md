# RK3588 Headless RKNN Lite Baseline Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a headless Python RKNN Lite inference baseline on `orange-rk3588`.

**Architecture:** Use a Python virtual environment on the board and install `rknn-toolkit-lite2` plus minimal numeric/image dependencies. Validate import first, then load `/usr/share/rknn_demo/mobilenet_ssd.rknn`, initialize RK3588 runtime, and record whether the NPU accepts the model.

**Tech Stack:** Python 3.11 on Orange Pi Bookworm, pip, `rknn-toolkit-lite2`, RKNN runtime files already present.

---

## Source Notes

PyPI currently describes `rknn-toolkit-lite2` as supporting AArch64 Linux and Python 3.7 through 3.12:

```text
https://pypi.org/project/rknn-toolkit-lite2/
```

Rockchip's RKNN Toolkit2 repository documents RKNN Toolkit Lite2 as the board-side deployment interface:

```text
https://github.com/rockchip-linux/rknn-toolkit2
```

There are community reports about some RKNN Lite versions misdetecting Linux aarch64 on RK3588. If the latest package fails, pin and test alternate versions rather than assuming the NPU is broken.

## Task 1: Create Python Virtual Environment

- [ ] **Step 1: Install venv support if needed**

Run:

```bash
SSHPASS="$EDGE_ORANGE_RK3588_PASSWORD" sshpass -e ssh -p 6280 orangepi@150.158.146.192 \
  'python3 -m venv --help >/dev/null 2>&1 || (printf "%s\n" "$EDGE_ORANGE_RK3588_PASSWORD" | sudo -S apt-get install -y python3-venv)'
```

- [ ] **Step 2: Create venv**

Run:

```bash
SSHPASS="$EDGE_ORANGE_RK3588_PASSWORD" sshpass -e ssh -p 6280 orangepi@150.158.146.192 \
  'mkdir -p ~/edge-model-lab && python3 -m venv ~/edge-model-lab/venv'
```

- [ ] **Step 3: Upgrade pip tooling**

Run:

```bash
SSHPASS="$EDGE_ORANGE_RK3588_PASSWORD" sshpass -e ssh -p 6280 orangepi@150.158.146.192 \
  '~/edge-model-lab/venv/bin/python -m pip install --upgrade pip setuptools wheel'
```

## Task 2: Install RKNN Lite Runtime

- [ ] **Step 1: Install packages**

Run:

```bash
SSHPASS="$EDGE_ORANGE_RK3588_PASSWORD" sshpass -e ssh -p 6280 orangepi@150.158.146.192 \
  '~/edge-model-lab/venv/bin/python -m pip install rknn-toolkit-lite2 numpy pillow'
```

- [ ] **Step 2: Verify imports**

Run:

```bash
SSHPASS="$EDGE_ORANGE_RK3588_PASSWORD" sshpass -e ssh -p 6280 orangepi@150.158.146.192 \
  '~/edge-model-lab/venv/bin/python - << "PY"
from rknnlite.api import RKNNLite
import numpy as np
print("RKNNLite import ok")
print("numpy", np.__version__)
PY'
```

## Task 3: Load RKNN Model And Initialize Runtime

- [ ] **Step 1: Create probe script**

Run:

```bash
SSHPASS="$EDGE_ORANGE_RK3588_PASSWORD" sshpass -e ssh -p 6280 orangepi@150.158.146.192 \
  'cat > ~/edge-model-lab/rknn_probe.py << "PY"
from rknnlite.api import RKNNLite

model = "/usr/share/rknn_demo/mobilenet_ssd.rknn"
rknn = RKNNLite(verbose=True)
print("load", model)
ret = rknn.load_rknn(model)
print("load_ret", ret)
if ret != 0:
    raise SystemExit(ret)

ret = rknn.init_runtime(target="rk3588")
print("init_ret", ret)
rknn.release()
raise SystemExit(0 if ret == 0 else 1)
PY'
```

- [ ] **Step 2: Run probe**

Run:

```bash
SSHPASS="$EDGE_ORANGE_RK3588_PASSWORD" sshpass -e ssh -p 6280 orangepi@150.158.146.192 \
  'timeout 30 ~/edge-model-lab/venv/bin/python ~/edge-model-lab/rknn_probe.py'
```

Expected: model load succeeds. Runtime init may expose RKNN Lite version compatibility issues; record exact output either way.

## Task 4: Record Result

- [ ] **Step 1: Create experiment note**

Create `docs/experiments/YYYY-MM-DD-rk3588-headless-rknn-lite-baseline.md` with:

- packages installed,
- import result,
- model load result,
- runtime init result,
- exact errors if any,
- temperature before/after,
- next remediation.

