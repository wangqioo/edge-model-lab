# RK3576 YOLO Smoke And Systemd Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a repeatable K7 RK3576 YOLOv5 demo smoke command and a first RK3576 systemd deployment skeleton.

**Architecture:** Add a focused `scripts/lib/yolo.py` module that extracts the local K7 demo archive, uploads it over the existing SCP helper, and runs the vendor binary remotely. Add CLI wiring and static systemd skeleton files. Record actual device results in an experiment note.

**Tech Stack:** Python stdlib, existing `edgectl`, SSH/SCP, vendor RKNN YOLOv5 binary, systemd unit files.

---

### Task 1: Add YOLO Smoke Runner

**Files:**
- Create: `scripts/lib/yolo.py`
- Modify: `scripts/lib/cli.py`

- [ ] **Step 1: Implement `scripts/lib/yolo.py`**

Create a module that:

- rejects non-RK3576 devices,
- extracts the K7 zip into a temp directory,
- uploads the extracted demo directory to `/tmp/edge-model-lab-yolo/k7_rk3576_yolov5s_demo`,
- runs `rknn_yolov5_demo` with `LD_LIBRARY_PATH=lib`.

- [ ] **Step 2: Add CLI command**

Add `yolo-smoke <device>` in `scripts/lib/cli.py`, look up the target device, and call `run_yolo_smoke(device)`.

- [ ] **Step 3: Verify compile**

Run:

```bash
python3 -m compileall scripts
```

Expected: exit 0.

### Task 2: Add Systemd Skeleton

**Files:**
- Create: `deploy/systemd/rk3576/README.md`
- Create: `deploy/systemd/rk3576/edge-rknn-yolo-smoke.service`

- [ ] **Step 1: Add README**

Document the target layout:

```text
/opt/edge/apps
/opt/edge/models
/opt/edge/logs
/opt/edge/run
```

Explain that this phase does not install or enable the service.

- [ ] **Step 2: Add one-shot service unit**

Add a service unit that runs `/opt/edge/apps/rknn_yolov5_demo/rknn_yolov5_demo` with the matching library path and logs through journald.

### Task 3: Run Device Verification

**Files:**
- Create: `docs/experiments/2026-06-25-rk3576-yolov5-demo-smoke.md`

- [ ] **Step 1: Run linaro smoke**

Run:

```bash
EDGE_LINARO_RK3576_PASSWORD='...' ./scripts/edgectl yolo-smoke linaro-rk3576
```

Expected: vendor demo exits 0 or prints an actionable missing dependency/runtime error that is recorded.

- [ ] **Step 2: Run lckfb smoke if linaro succeeds**

Run:

```bash
EDGE_LCKFB_RK3576_PASSWORD='...' ./scripts/edgectl yolo-smoke lckfb-rk3576
```

Expected: same as linaro, but record memory/runtime differences.

- [ ] **Step 3: Write experiment note**

Record command output, runtime versions if visible, success/failure status, and next actions.

### Task 4: Final Verification And Commit

**Files:**
- All files above

- [ ] **Step 1: Run local verification**

Run:

```bash
python3 -m compileall scripts
./scripts/edgectl models --platform rk3576
```

Expected: exit 0.

- [ ] **Step 2: Commit**

Run:

```bash
git add scripts/lib/yolo.py scripts/lib/cli.py deploy/systemd/rk3576 docs/experiments/2026-06-25-rk3576-yolov5-demo-smoke.md docs/superpowers/specs/2026-06-25-rk3576-yolo-systemd-design.md docs/superpowers/plans/2026-06-25-rk3576-yolo-systemd.md
git commit -m "feat: add rk3576 yolo smoke"
```
