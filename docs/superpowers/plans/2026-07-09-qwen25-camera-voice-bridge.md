# Qwen2.5 Camera Voice Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a localhost camera and voice bridge for the RK1828 Qwen2.5-Omni-3B Vision+LLM service.

**Architecture:** Extend the board service with a JSON inference endpoint, then add a Mac-local stdlib HTTP bridge that serves the camera UI and proxies image+prompt requests to the board. Browser Web APIs provide camera, speech-to-text, and speech synthesis.

**Tech Stack:** Python 3 stdlib, `http.server`, `urllib.request`, browser `getUserMedia`, Web Speech API, systemd on RK3588.

---

### Task 1: Board JSON Endpoint

**Files:**
- Modify: `deploy/apps/rk1828/qwen25_omni_vlm_web.py`
- Modify: `tests/test_qwen25_omni_vlm_web.py`

- [ ] Write failing tests for JSON inference payload formatting.
- [ ] Implement a reusable `infer_uploaded_image()` helper and `POST /api/infer`.
- [ ] Verify `python3 -m unittest tests/test_qwen25_omni_vlm_web.py`.

### Task 2: Local Camera Bridge

**Files:**
- Create: `deploy/apps/rk1828/qwen25_omni_camera_bridge.py`
- Create: `tests/test_qwen25_omni_camera_bridge.py`

- [ ] Write failing tests for multipart body construction and camera page contents.
- [ ] Implement the local HTTP server, camera page, `/health`, and `/infer` proxy.
- [ ] Verify `python3 -m unittest tests/test_qwen25_omni_camera_bridge.py`.

### Task 3: Board Deploy

**Files:**
- Board: `/home/orangepi/lincaigui/qwen25-omni-vlm-web/qwen25_omni_vlm_web.py`

- [ ] Copy the updated board app.
- [ ] Restart `qwen25-omni-vlm-web.service`.
- [ ] Verify `/health`, `/api/infer`, and Qwen3-VL restoration.

### Task 4: Local Run

**Files:**
- Local: `deploy/apps/rk1828/qwen25_omni_camera_bridge.py`

- [ ] Start the local bridge on `127.0.0.1:8894`.
- [ ] Open `http://localhost:8894`.
- [ ] Verify camera preview, microphone button availability, one request, spoken response, and history rendering.
