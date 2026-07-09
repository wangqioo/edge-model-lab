# Qwen2.5-Omni VLM Test Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add and deploy a separate browser test console for Qwen2.5-Omni-3B Vision+LLM on the RK3588 + RK1828K host.

**Architecture:** A stdlib-only Python HTTP server accepts image uploads and prompts, calls the existing Qwen2.5-Omni VLM script, and serializes RK1828 access by stopping and restarting `rkllm3-server.service` around inference. A separate systemd unit listens on port `8892`.

**Tech Stack:** Python 3.11 stdlib, `http.server`, `cgi.FieldStorage`, `subprocess`, systemd.

---

### Task 1: Local Web App Helpers

**Files:**
- Create: `deploy/apps/rk1828/qwen25_omni_vlm_web.py`
- Create: `tests/test_qwen25_omni_vlm_web.py`

- [ ] Write failing unit tests for stdout parsing and HTML rendering.
- [ ] Run `python3 -m unittest tests/test_qwen25_omni_vlm_web.py` and confirm failure because the module is missing.
- [ ] Implement the helper functions in `qwen25_omni_vlm_web.py`.
- [ ] Re-run the unit test and confirm it passes.

### Task 2: HTTP Upload Flow

**Files:**
- Modify: `deploy/apps/rk1828/qwen25_omni_vlm_web.py`
- Modify: `tests/test_qwen25_omni_vlm_web.py`

- [ ] Write failing tests for upload validation.
- [ ] Implement multipart image validation and temporary file writing.
- [ ] Re-run `python3 -m unittest tests/test_qwen25_omni_vlm_web.py`.

### Task 3: Systemd Unit

**Files:**
- Create: `deploy/systemd/rk1828/qwen25-omni-vlm-web.service`
- Modify: `docs/guides/rk1828k-bringup-lessons.md`

- [ ] Add a systemd unit for port `8892`.
- [ ] Document service checks and the shared-RK1828 limitation.
- [ ] Run local syntax checks.

### Task 4: Board Deploy and Verification

**Files:**
- Board: `/home/orangepi/lincaigui/qwen25-omni-vlm-web/qwen25_omni_vlm_web.py`
- Board: `/etc/systemd/system/qwen25-omni-vlm-web.service`

- [ ] Copy the app and systemd unit to the RK3588 host.
- [ ] Enable and start the service.
- [ ] Verify `/health` on `127.0.0.1:8892`.
- [ ] Verify current Qwen3-VL chat health on `127.0.0.1:8888/api/health`.
- [ ] Run a manual image request if safe and confirm Qwen3-VL is restored.
