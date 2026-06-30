from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
from pathlib import Path

from .config import Device
from .ssh import run_scp_to_device, run_ssh


RKNN_TOOLKIT2_ARCHIVE = Path(
    "/Users/wq/Documents/ZSPACE/sata11-15850752485/百度网盘下载/K7 rk3576/3-SoftwareData/RKNPU/rknn-toolkit2.zip"
)
RKNN_LITE_WHEEL_MEMBER = (
    "rknn-toolkit2/rknn-toolkit-lite2/packages/"
    "rknn_toolkit_lite2-2.0.0b0-cp311-cp311-linux_aarch64.whl"
)
RKNN_LITE_WHEEL_NAME = "rknn_toolkit_lite2-2.0.0b0-cp311-cp311-linux_aarch64.whl"
REMOTE_BOOTSTRAP_DIR = "/tmp/edge-model-lab-bootstrap"


REMOTE_BOOTSTRAP_SCRIPT = r"""
set -eu
SUDO_PASSWORD="$1"
WHEEL_PATH="$2"
BASE_DIR="$HOME/edge-model-lab"
VENV_DIR="$BASE_DIR/venv"
PYTHON_BIN="$VENV_DIR/bin/python"
PROBE_VENV="/tmp/edge-venv-probe-$$"

echo "## python"
python3 --version

if ! python3 -m venv "$PROBE_VENV" >/dev/null 2>&1; then
  echo "## apt install python3-venv python3-pip"
  rm -rf "$PROBE_VENV"
  if sudo -n true 2>/dev/null; then
    sudo apt-get update
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3.11-venv python3-venv python3-pip
  elif [ -n "$SUDO_PASSWORD" ]; then
    printf '%s\n' "$SUDO_PASSWORD" | sudo -S apt-get update
    printf '%s\n' "$SUDO_PASSWORD" | sudo -S DEBIAN_FRONTEND=noninteractive apt-get install -y python3.11-venv python3-venv python3-pip
  else
    echo "sudo password is required to install python3-venv"
    exit 30
  fi
else
  rm -rf "$PROBE_VENV"
fi

mkdir -p "$BASE_DIR"
if [ ! -x "$PYTHON_BIN" ]; then
  python3 -m venv "$VENV_DIR"
fi
if ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
  rm -rf "$VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

echo "## pip packages"
"$PYTHON_BIN" -m pip install --disable-pip-version-check numpy psutil ruamel.yaml "$WHEEL_PATH"

echo "## import"
"$PYTHON_BIN" - <<'PY'
import numpy
import psutil
import ruamel.yaml
from rknnlite.api import RKNNLite

print("numpy", numpy.__version__)
print("psutil", psutil.__version__)
print("rknnlite_import=ok")
print("rknnlite_class", RKNNLite.__name__)
PY

echo "## librknnrt"
if [ -f /usr/lib/librknnrt.so ]; then
  strings /usr/lib/librknnrt.so | grep -m1 'librknnrt version' || true
  ls -lh /usr/lib/librknnrt.so
else
  echo "/usr/lib/librknnrt.so missing"
fi
"""


def _extract_wheel(output_dir: Path) -> Path:
    subprocess.run(
        ["bsdtar", "-xf", str(RKNN_TOOLKIT2_ARCHIVE), "-C", str(output_dir), RKNN_LITE_WHEEL_MEMBER],
        check=True,
        capture_output=True,
        text=True,
    )
    extracted = output_dir / RKNN_LITE_WHEEL_MEMBER
    target = output_dir / RKNN_LITE_WHEEL_NAME
    extracted.rename(target)
    return target


def bootstrap_rknn_lite(device: Device) -> int:
    with tempfile.TemporaryDirectory(prefix="edge-rknn-lite-wheel-") as temp_name:
        temp_dir = Path(temp_name)
        try:
            wheel_path = _extract_wheel(temp_dir)
        except subprocess.CalledProcessError as exc:
            print(f"failed to extract RKNN Lite wheel: {exc.stderr.strip()}")
            return 2

        mkdir_code, mkdir_output = run_ssh(device, f"mkdir -p {shlex.quote(REMOTE_BOOTSTRAP_DIR)}", timeout_seconds=20)
        if mkdir_code != 0:
            print(mkdir_output.rstrip())
            return mkdir_code

        remote_wheel = f"{REMOTE_BOOTSTRAP_DIR}/{RKNN_LITE_WHEEL_NAME}"
        scp_code, scp_output = run_scp_to_device(device, wheel_path, remote_wheel)
        if scp_code != 0:
            print(scp_output.rstrip())
            return scp_code

    sudo_password = ""
    if device.password_env:
        sudo_password = os.environ.get(device.password_env, "")

    command = (
        "cat > /tmp/edge-rknn-bootstrap.sh <<'SH'\n"
        f"{REMOTE_BOOTSTRAP_SCRIPT}\n"
        "SH\n"
        "chmod +x /tmp/edge-rknn-bootstrap.sh\n"
        f"/tmp/edge-rknn-bootstrap.sh {shlex.quote(sudo_password)} {shlex.quote(remote_wheel)}"
    )
    print(f"===== RKNN Lite bootstrap {device.id} =====")
    code, output = run_ssh(device, command, timeout_seconds=600)
    if output:
        print(output.rstrip())
    return code
