from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
from pathlib import Path

from .assets import load_assets
from .config import Device, PROJECT_ROOT
from .rknn import _extract_asset
from .ssh import run_scp_to_device, run_ssh


SERVICE_APP = PROJECT_ROOT / "deploy/apps/rknn_service/edge_rknn_service.py"
SERVICE_UNIT = PROJECT_ROOT / "deploy/systemd/rk3576/edge-rknn-python.service"
MODEL_ASSET_ID = "rk3576_resnet18_lite2"
REMOTE_TMP = "/tmp/edge-model-lab-rknn-service"
REMOTE_APP_DIR = "/opt/edge/apps/rknn_service"
REMOTE_MODEL = "/opt/edge/models/rk3576_resnet18_lite2.rknn"
REMOTE_UNIT = "/etc/systemd/system/edge-rknn-python.service"
SERVICE_URL = "http://127.0.0.1:18080"


BENCH_REMOTE_SCRIPT = r"""
set -eu
COUNT="$1"

snapshot() {
  LABEL="$1"
  echo "## ${LABEL}"
  awk '/MemTotal|MemAvailable/ { print }' /proc/meminfo
  printf 'loadavg='
  cat /proc/loadavg
  for z in /sys/class/thermal/thermal_zone*; do
    [ -d "$z" ] || continue
    type="$(cat "$z/type" 2>/dev/null || true)"
    temp="$(cat "$z/temp" 2>/dev/null || true)"
    if [ -n "$temp" ]; then
      awk -v zone="$z" -v typ="$type" -v raw="$temp" 'BEGIN { printf "%s type=%s temp_c=%.1f\n", zone, typ, raw / 1000 }'
    fi
  done
}

snapshot "before"
echo "## benchmark"
curl -fsS "http://127.0.0.1:18080/bench/synthetic?count=${COUNT}"
echo
snapshot "after"
"""


def deploy_rknn_service(device: Device) -> int:
    if device.platform != "rk3576":
        print(f"RKNN Python service deploy targets rk3576, device {device.id} is {device.platform}")
        return 2

    assets = load_assets()
    asset = assets[MODEL_ASSET_ID]
    with tempfile.TemporaryDirectory(prefix="edge-rknn-service-") as temp_name:
        temp_dir = Path(temp_name)
        try:
            model_path = _extract_asset(asset, temp_dir)
        except subprocess.CalledProcessError as exc:
            print(f"failed to extract service assets: {exc.stderr.strip()}")
            return 2

        mkdir_code, mkdir_output = run_ssh(device, f"mkdir -p {shlex.quote(REMOTE_TMP)}", timeout_seconds=20)
        if mkdir_code != 0:
            print(mkdir_output.rstrip())
            return mkdir_code

        uploads = [
            (SERVICE_APP, f"{REMOTE_TMP}/edge_rknn_service.py"),
            (SERVICE_UNIT, f"{REMOTE_TMP}/edge-rknn-python.service"),
            (model_path, f"{REMOTE_TMP}/rk3576_resnet18_lite2.rknn"),
        ]
        for local_path, remote_path in uploads:
            scp_code, scp_output = run_scp_to_device(device, Path(local_path), remote_path)
            if scp_code != 0:
                print(scp_output.rstrip())
                return scp_code

    sudo_password = ""
    if device.password_env:
        sudo_password = os.environ.get(device.password_env, "")
    remote_script = f"""
set -eu
SUDO_PASSWORD={shlex.quote(sudo_password)}
run_sudo() {{
  printf '%s\\n' "$SUDO_PASSWORD" | sudo -S -p '' "$@"
}}

echo "## edge-user"
if ! id -u edge >/dev/null 2>&1; then
  run_sudo useradd --system --home-dir /opt/edge --create-home --shell /usr/sbin/nologin edge
fi
if id -nG edge | tr ' ' '\\n' | grep -qx video; then :; else run_sudo usermod -aG video edge; fi
if id -nG edge | tr ' ' '\\n' | grep -qx render; then :; else run_sudo usermod -aG render edge; fi

echo "## install"
run_sudo install -d -o edge -g edge /opt/edge /opt/edge/apps /opt/edge/models /opt/edge/logs /opt/edge/run {shlex.quote(REMOTE_APP_DIR)}
run_sudo cp {shlex.quote(REMOTE_TMP)}/edge_rknn_service.py {shlex.quote(REMOTE_APP_DIR)}/edge_rknn_service.py
run_sudo cp {shlex.quote(REMOTE_TMP)}/rk3576_resnet18_lite2.rknn {shlex.quote(REMOTE_MODEL)}
run_sudo chmod 0755 {shlex.quote(REMOTE_APP_DIR)}/edge_rknn_service.py
run_sudo chown -R edge:edge /opt/edge/apps /opt/edge/models /opt/edge/logs /opt/edge/run

echo "## venv"
VENV_PYTHON={shlex.quote(f"/home/{device.user}/edge-model-lab/venv/bin/python")}
if [ ! -x "$VENV_PYTHON" ]; then
  echo "missing venv python: $VENV_PYTHON"
  exit 40
fi
"$VENV_PYTHON" -c 'import numpy; from rknnlite.api import RKNNLite; print("venv_import=ok")'

echo "## systemd"
sed -e "s#__EDGE_VENV_PYTHON__#$VENV_PYTHON#g" -e "s#__EDGE_SERVICE_USER__#{shlex.quote(device.user)}#g" {shlex.quote(REMOTE_TMP)}/edge-rknn-python.service > /tmp/edge-rknn-python.service.rendered
run_sudo install -m 0644 /tmp/edge-rknn-python.service.rendered {shlex.quote(REMOTE_UNIT)}
run_sudo systemctl daemon-reload
run_sudo systemctl restart edge-rknn-python.service
sleep 2
run_sudo systemctl status --no-pager edge-rknn-python.service

echo "## health"
curl -fsS http://127.0.0.1:18080/health
echo
echo "## synthetic"
curl -fsS http://127.0.0.1:18080/infer/synthetic
echo
"""
    print(f"===== RKNN Python service deploy {device.id} =====")
    code, output = run_ssh(device, "sh -s", timeout_seconds=240, stdin=remote_script)
    if output:
        print(output.rstrip())
    return code


def bench_rknn_service(device: Device, count: int) -> int:
    if count < 1:
        print("count must be >= 1")
        return 2
    if count > 200:
        print("count must be <= 200")
        return 2

    print(f"===== RKNN Python service bench {device.id} count={count} =====")
    code, output = run_ssh(
        device,
        f"sh -s -- {shlex.quote(str(count))}",
        timeout_seconds=max(30, count * 3),
        stdin=BENCH_REMOTE_SCRIPT,
    )
    if output:
        print(output.rstrip())
    return code
