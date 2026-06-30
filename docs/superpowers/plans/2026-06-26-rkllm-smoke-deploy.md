# RKLLM Smoke Deploy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reliable TaishanPi RK3576 RKLLM smoke/deploy command without mixing it into the RKNN deploy path.

**Architecture:** Keep RKNN deploy/bench unchanged. Add a dedicated RKLLM smoke path for `lckfb-rk3576` that uploads the vendor demo bundle, installs files with explicit checks, and starts the vendor demo via a one-shot systemd unit or direct smoke command. Make `deploy all` continue to target RKNN only.

**Tech Stack:** Python 3.11, subprocess/ssh/scp, systemd, existing scripts/lib helpers, unittest.

---

### Task 1: Split RKLLM into its own command path

**Files:**
- Modify: `scripts/lib/cli.py`
- Modify: `scripts/lib/deploy.py`
- Modify: `tests/test_deploy.py`

- [ ] **Step 1: Write the failing test**

```python
def test_llm_deploy_is_separate_from_general_deploy():
    from scripts.lib import deploy
    device = Device(... id="lckfb-rk3576", platform="rk3576" ...)
    with patch.object(deploy, "deploy_rkllm_device", return_value=0) as mock_llm, patch.object(
        deploy, "deploy_rknn_service", return_value=0
    ) as mock_rknn:
        code = deploy.deploy_llm_device(device)
    assert code == 0
    mock_llm.assert_called_once_with(device)
    mock_rknn.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_deploy.DeployRoutingTests.test_llm_deploy_is_separate_from_general_deploy -v`
Expected: FAIL because the test does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def deploy_device(device: Device) -> int:
    if device.platform == "rk3576":
        return deploy_rknn_service(device)
    if device.platform == "rk3588":
        return deploy_rknn_service(device)
    print(f"no deploy recipe for {device.platform}")
    return 2
```

```python
if args.command == "llm-deploy":
    ...
    return deploy_llm_device(device)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_deploy -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/cli.py scripts/lib/deploy.py tests/test_deploy.py
git commit -m "feat: separate rkllm smoke deploy"
```

### Task 2: Make RKLLM installation explicit and observable

**Files:**
- Modify: `scripts/lib/deploy.py`
- Modify: `scripts/lib/ssh.py`
- Modify: `tests/test_deploy.py`

- [ ] **Step 1: Write the failing test**

```python
def test_run_scp_to_device_uses_legacy_scp():
    from scripts.lib.ssh import run_scp_to_device
    assert True  # mock subprocess.run and assert '-O' is present in argv
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_deploy -v`
Expected: the new scp assertion fails before the code change.

- [ ] **Step 3: Write minimal implementation**

```python
command = ["scp", "-O", "-P", str(device.port), ...]
```

```python
def deploy_rkllm_device(device: Device) -> int:
    ...
    # upload files
    # create dirs
    # install files with checks
    # render unit
    # start service
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_deploy -v && python3 -m compileall scripts tests`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/deploy.py scripts/lib/ssh.py tests/test_deploy.py
git commit -m "fix: make rkllm upload path compatible"
```

### Task 3: Add README and experiment notes

**Files:**
- Modify: `README.md`
- Create: `docs/experiments/2026-06-26-rkllm-qwen3-vl-smoke.md`

- [ ] **Step 1: Write the note**

```md
# RKLLM Qwen3-VL smoke

Describe the vendor demo bundle, the supported device, the smoke command, and the fact that it is separate from RKNN deploy.
```

- [ ] **Step 2: Run a doc sanity check**

Run: `rg -n "llm-deploy|rkllm|Qwen3-VL" README.md docs/experiments`
Expected: entries exist in README and the new experiment note.

- [ ] **Step 3: Commit**

```bash
git add README.md docs/experiments/2026-06-26-rkllm-qwen3-vl-smoke.md
git commit -m "docs: add rkllm smoke notes"
```

### Task 4: Verify end-to-end on lckfb-rk3576

**Files:**
- No code changes expected

- [ ] **Step 1: Run the smoke command**

Run: `EDGE_LCKFB_RK3576_PASSWORD='...' ./scripts/edgectl llm-deploy lckfb-rk3576`
Expected: systemd status or demo output prints successfully.

- [ ] **Step 2: Check the service state**

Run: `./scripts/edgectl service-status lckfb-rk3576 edge-rkllm-qwen3-vl.service`
Expected: unit exists and is readable.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: add rkllm smoke deployment"
```
