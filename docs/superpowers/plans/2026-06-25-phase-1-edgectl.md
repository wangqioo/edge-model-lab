# Phase 1 Edgectl Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first usable `edgectl` command for listing configured devices and running read-only health checks over SSH.

**Architecture:** `scripts/edgectl` is a Python 3 CLI backed by `devices.yaml`. It loads public device metadata, optionally reads password environment variable names from `devices.local.yaml`, and runs bounded SSH commands with clear text output. Health checks must not modify target devices.

**Tech Stack:** Python 3.13 on the Mac control machine, PyYAML for YAML parsing, OpenSSH for remote execution, optional `sshpass` only when a password environment variable is configured.

---

### Task 1: Add CLI Skeleton And Device Listing

**Files:**
- Create: `scripts/edgectl`
- Create: `scripts/lib/__init__.py`
- Create: `scripts/lib/config.py`
- Create: `scripts/lib/cli.py`

- [ ] **Step 1: Create config loader**

Create `scripts/lib/config.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEVICES_FILE = PROJECT_ROOT / "devices.yaml"
LOCAL_FILE = PROJECT_ROOT / "devices.local.yaml"


@dataclass(frozen=True)
class Device:
    id: str
    host: str
    port: int
    user: str
    role: str
    platform: str
    board: str
    deployment_backend: str
    report: str
    password_env: str | None = None


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def load_devices() -> dict[str, Device]:
    raw = _read_yaml(DEVICES_FILE)
    local = _read_yaml(LOCAL_FILE)
    raw_devices = raw.get("devices", {})
    if not isinstance(raw_devices, dict):
        raise ValueError("devices.yaml must contain a 'devices' mapping")

    local_auth = local.get("auth", {})
    if local_auth is None:
        local_auth = {}
    if not isinstance(local_auth, dict):
        raise ValueError("devices.local.yaml auth must be a mapping")

    devices: dict[str, Device] = {}
    for device_id, values in raw_devices.items():
        if not isinstance(values, dict):
            raise ValueError(f"Device {device_id} must be a mapping")
        auth_values = local_auth.get(device_id, {})
        if auth_values is None:
            auth_values = {}
        if not isinstance(auth_values, dict):
            raise ValueError(f"Auth override for {device_id} must be a mapping")

        devices[device_id] = Device(
            id=device_id,
            host=str(values["host"]),
            port=int(values["port"]),
            user=str(values["user"]),
            role=str(values["role"]),
            platform=str(values["platform"]),
            board=str(values["board"]),
            deployment_backend=str(values["deployment_backend"]),
            report=str(values["report"]),
            password_env=auth_values.get("password_env"),
        )
    return devices
```

- [ ] **Step 2: Create CLI list command**

Create `scripts/lib/cli.py`:

```python
from __future__ import annotations

import argparse
import sys

from .config import Device, load_devices


def _print_device_table(devices: dict[str, Device]) -> None:
    headers = ("id", "platform", "role", "backend", "ssh", "board")
    rows = [
        (
            device.id,
            device.platform,
            device.role,
            device.deployment_backend,
            f"{device.user}@{device.host}:{device.port}",
            device.board,
        )
        for device in devices.values()
    ]
    widths = [
        max(len(str(row[index])) for row in (headers, *rows))
        for index in range(len(headers))
    ]
    print("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(str(value).ljust(widths[index]) for index, value in enumerate(row)))


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="edgectl")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="List configured edge devices")

    args = parser.parse_args(argv)
    devices = load_devices()

    if args.command == "list":
        _print_device_table(devices)
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
```

- [ ] **Step 3: Create executable wrapper**

Create `scripts/edgectl`:

```python
#!/usr/bin/env python3
from lib.cli import run

raise SystemExit(run())
```

Run:

```bash
chmod +x scripts/edgectl
./scripts/edgectl list
```

Expected: A table with all three configured devices.

### Task 2: Add SSH Runner And Health Checks

**Files:**
- Modify: `scripts/lib/cli.py`
- Create: `scripts/lib/ssh.py`
- Create: `scripts/lib/health.py`

- [ ] **Step 1: Create SSH runner**

Create `scripts/lib/ssh.py`:

```python
from __future__ import annotations

import os
import shutil
import subprocess

from .config import Device


def run_ssh(device: Device, remote_command: str, timeout_seconds: int = 20) -> tuple[int, str]:
    base = [
        "ssh",
        "-p",
        str(device.port),
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "ConnectTimeout=8",
        f"{device.user}@{device.host}",
        remote_command,
    ]

    env = os.environ.copy()
    command = base
    if device.password_env:
        password = os.environ.get(device.password_env)
        if password:
            sshpass = shutil.which("sshpass")
            if not sshpass:
                return 127, f"sshpass is required because {device.password_env} is set in local config\n"
            command = [
                sshpass,
                "-e",
                "ssh",
                "-p",
                str(device.port),
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "ConnectTimeout=8",
                f"{device.user}@{device.host}",
                remote_command,
            ]
            env["SSHPASS"] = password

    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            env=env,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return 124, f"Timed out after {timeout_seconds}s\n"

    return completed.returncode, completed.stdout + completed.stderr
```

- [ ] **Step 2: Create health command implementation**

Create `scripts/lib/health.py`:

```python
from __future__ import annotations

from .config import Device
from .ssh import run_ssh


HEALTH_SCRIPT = r"""
set +e
echo "## identity"
hostname
id
echo
echo "## os"
cat /etc/os-release 2>/dev/null | sed -n '1,8p'
uname -a
uptime
echo
echo "## memory"
free -h 2>/dev/null || cat /proc/meminfo | head -5
echo
echo "## storage"
df -hT / /boot /var/log 2>/dev/null
echo
echo "## thermal"
for z in /sys/class/thermal/thermal_zone*; do
  [ -d "$z" ] || continue
  type="$(cat "$z/type" 2>/dev/null)"
  temp="$(cat "$z/temp" 2>/dev/null)"
  if [ -n "$temp" ]; then
    awk -v zone="$z" -v typ="$type" -v raw="$temp" 'BEGIN { printf "%s type=%s temp_c=%.1f\n", zone, typ, raw / 1000 }'
  fi
done
echo
echo "## runtimes"
command -v docker >/dev/null 2>&1 && docker --version || echo "docker: missing"
command -v containerd >/dev/null 2>&1 && containerd --version || echo "containerd: missing"
command -v python3 >/dev/null 2>&1 && python3 --version || echo "python3: missing"
command -v pip3 >/dev/null 2>&1 && pip3 --version || echo "pip3: missing"
echo
echo "## rockchip"
ls -la /usr/bin/rknn_server /usr/bin/rknn_demo /usr/lib/librknnrt.so /usr/lib/librknn_api.so 2>/dev/null || true
ls -la /dev/mali* /dev/rga* /dev/dma_heap* /dev/dri/renderD* 2>/dev/null || true
find /sys -maxdepth 4 \( -iname '*npu*' -o -iname '*rknpu*' -o -iname '*rga*' -o -iname '*mali*' \) 2>/dev/null | head -40
echo
echo "## failed-units"
systemctl --failed --no-pager 2>/dev/null || true
"""


def print_health(device: Device) -> int:
    print(f"===== {device.id} ({device.user}@{device.host}:{device.port}) =====")
    code, output = run_ssh(device, f"sh -c {HEALTH_SCRIPT!r}", timeout_seconds=35)
    if code != 0:
        print(f"health check failed with exit code {code}")
    print(output.rstrip())
    print()
    return code
```

- [ ] **Step 3: Wire health into CLI**

Modify `scripts/lib/cli.py`:

```python
from __future__ import annotations

import argparse
import sys

from .config import Device, load_devices
from .health import print_health


def _print_device_table(devices: dict[str, Device]) -> None:
    headers = ("id", "platform", "role", "backend", "ssh", "board")
    rows = [
        (
            device.id,
            device.platform,
            device.role,
            device.deployment_backend,
            f"{device.user}@{device.host}:{device.port}",
            device.board,
        )
        for device in devices.values()
    ]
    widths = [
        max(len(str(row[index])) for row in (headers, *rows))
        for index in range(len(headers))
    ]
    print("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(str(value).ljust(widths[index]) for index, value in enumerate(row)))


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="edgectl")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="List configured edge devices")
    health_parser = subparsers.add_parser("health", help="Run read-only device health checks")
    health_parser.add_argument("target", help="Device id or 'all'")

    args = parser.parse_args(argv)
    devices = load_devices()

    if args.command == "list":
        _print_device_table(devices)
        return 0

    if args.command == "health":
        if args.target == "all":
            exit_code = 0
            for device in devices.values():
                exit_code = max(exit_code, print_health(device))
            return exit_code
        device = devices.get(args.target)
        if not device:
            parser.error(f"Unknown device: {args.target}")
        return print_health(device)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
```

Run:

```bash
./scripts/edgectl health orange-rk3588
```

Expected: If SSH key auth is not configured yet, the command exits nonzero and reports auth failure. With local password environment configured, it prints health sections.

### Task 3: Document Credential Setup And Verify

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add credential setup docs**

Append to `README.md`:

```markdown
## Local Credential Setup

Preferred setup is SSH key auth to each board.

For temporary password auth:

```bash
cp devices.local.example.yaml devices.local.yaml
export EDGE_ORANGE_RK3588_PASSWORD='...'
export EDGE_LINARO_RK3576_PASSWORD='...'
export EDGE_LCKFB_RK3576_PASSWORD='...'
```

`devices.local.yaml` is ignored by git.
```

- [ ] **Step 2: Verify commands**

Run:

```bash
./scripts/edgectl list
python3 -m compileall scripts
git status --short
```

Expected:

- `edgectl list` prints all three devices.
- `compileall` exits 0.
- `git status --short` shows the new project files.

- [ ] **Step 3: Optional live health verification**

If password environment variables are available in the current shell, run:

```bash
./scripts/edgectl health all
```

Expected:

- All three devices print health reports.
- Exit code is 0 if all SSH checks succeed.

