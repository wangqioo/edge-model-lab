# RK3588 RKNN Demo Remediation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the built-in `rknn_demo` runnable on `orange-rk3588` with minimal controlled package/library changes.

**Architecture:** Treat the Orange Pi as the only target for this remediation. First install standard Debian shared-library packages, then resolve Rockchip-specific `librga` and MPP libraries from installed vendor packages or explicit package searches. Verify with `ldd` before running any demo.

**Tech Stack:** SSH, apt on Orange Pi Bookworm, RKNN demo binaries already on the board.

---

### Task 1: Install Standard Runtime Libraries

**Files:**
- No repository files changed unless experiment notes are updated.

- [ ] **Step 1: Capture pre-change package state**

Run:

```bash
SSHPASS="$EDGE_ORANGE_RK3588_PASSWORD" sshpass -e ssh -p 6280 orangepi@150.158.146.192 \
  'dpkg -l | egrep "libdrm2|libfreetype6|libpixman-1-0|librga|mpp|rockchip" || true'
```

Expected: `libdrm2`, `libfreetype6`, and `libpixman-1-0` are not installed.

- [ ] **Step 2: Install Debian runtime libraries**

Run:

```bash
SSHPASS="$EDGE_ORANGE_RK3588_PASSWORD" sshpass -e ssh -p 6280 orangepi@150.158.146.192 \
  'sudo apt-get update && sudo apt-get install -y libdrm2 libfreetype6 libpixman-1-0'
```

Expected: apt exits 0.

- [ ] **Step 3: Verify remaining missing libraries**

Run:

```bash
SSHPASS="$EDGE_ORANGE_RK3588_PASSWORD" sshpass -e ssh -p 6280 orangepi@150.158.146.192 \
  'ldd /usr/bin/rknn_demo 2>&1 | egrep "not found|librga|rockchip|drm|freetype|pixman"'
```

Expected: `libdrm`, `libfreetype`, and `libpixman` are resolved. `librga.so` and `librockchip_mpp.so.1` may remain unresolved.

### Task 2: Resolve Rockchip-Specific Libraries

**Files:**
- No repository files changed unless experiment notes are updated.

- [ ] **Step 1: Search package cache**

Run:

```bash
SSHPASS="$EDGE_ORANGE_RK3588_PASSWORD" sshpass -e ssh -p 6280 orangepi@150.158.146.192 \
  'apt-cache search "rockchip\\|rga\\|mpp"'
```

Expected: Candidate package names for RGA/MPP, if available from configured repos.

- [ ] **Step 2: Search local filesystem**

Run:

```bash
SSHPASS="$EDGE_ORANGE_RK3588_PASSWORD" sshpass -e ssh -p 6280 orangepi@150.158.146.192 \
  'find /usr /lib /opt -name "librga.so*" -o -name "librockchip_mpp.so*" 2>/dev/null | sort'
```

Expected: Either paths exist and linker configuration can be corrected, or libraries are absent and need package installation.

- [ ] **Step 3: Install or link only after identifying source**

If packages exist, install the package names found in Task 2 Step 1.

If libraries exist outside linker paths, prefer adding a linker config file under `/etc/ld.so.conf.d/` and running `sudo ldconfig` over copying libraries.

Expected: `ldd /usr/bin/rknn_demo` reports no `not found` entries.

### Task 3: Run Bounded Demo Probe

**Files:**
- Modify: `docs/experiments/YYYY-MM-DD-rk3588-rknn-demo-remediation.md`

- [ ] **Step 1: Run help command with timeout**

Run:

```bash
SSHPASS="$EDGE_ORANGE_RK3588_PASSWORD" sshpass -e ssh -p 6280 orangepi@150.158.146.192 \
  'timeout 8 /usr/bin/rknn_demo --help 2>&1 || true'
```

Expected: The binary starts and prints usage text or a controlled runtime message. It must not fail with missing shared libraries.

- [ ] **Step 2: Record result**

Create or update an experiment note with:

- packages installed,
- final `ldd` result,
- demo command result,
- temperature before and after,
- any remaining blocker.

