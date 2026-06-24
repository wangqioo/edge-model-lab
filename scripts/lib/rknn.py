from __future__ import annotations

import shlex
import subprocess
import tempfile
from pathlib import Path

from .assets import ModelAsset
from .config import Device
from .ssh import run_scp_to_device, run_ssh


REMOTE_BASE = "/tmp/edge-model-lab-smoke"
DEFAULT_PYTHON_TEMPLATE = "/home/{user}/edge-model-lab/venv/bin/python"


RKNN_SMOKE_SCRIPT = r"""
set -eu
MODEL_PATH="$1"
PYTHON_BIN="$2"
"$PYTHON_BIN" - "$MODEL_PATH" <<'PY'
import sys
import time

model_path = sys.argv[1]

try:
    from rknnlite.api import RKNNLite
except Exception as exc:
    print(f"import_error={type(exc).__name__}: {exc}")
    raise SystemExit(20)

rknn = RKNNLite()
started = time.time()
load_ret = rknn.load_rknn(model_path)
print(f"load_ret={load_ret}")
if load_ret != 0:
    rknn.release()
    raise SystemExit(21)

init_ret = rknn.init_runtime()
elapsed_ms = int((time.time() - started) * 1000)
print(f"init_ret={init_ret}")
print(f"elapsed_ms={elapsed_ms}")
rknn.release()
raise SystemExit(0 if init_ret == 0 else 22)
PY
"""


def _extract_asset(asset: ModelAsset, output_dir: Path) -> Path:
    source = Path(asset.path)
    if asset.archive_member:
        subprocess.run(
            ["bsdtar", "-xf", str(source), "-C", str(output_dir), asset.archive_member],
            check=True,
            capture_output=True,
            text=True,
        )
        return output_dir / asset.archive_member
    return source


def run_rknn_smoke(device: Device, asset: ModelAsset, python_bin: str | None) -> int:
    if asset.kind != "rknn":
        print(f"Asset {asset.id} is {asset.kind}, not rknn")
        return 2
    if asset.platform != device.platform:
        print(f"Asset {asset.id} targets {asset.platform}, device {device.id} is {device.platform}")
        return 2

    with tempfile.TemporaryDirectory(prefix="edge-rknn-asset-") as temp_name:
        temp_dir = Path(temp_name)
        try:
            local_model = _extract_asset(asset, temp_dir)
        except subprocess.CalledProcessError as exc:
            print(f"failed to extract {asset.id}: {exc.stderr.strip()}")
            return 2

        if not local_model.exists():
            print(f"asset file not found after extract: {local_model}")
            return 2

        remote_model = f"{REMOTE_BASE}/{asset.id}.rknn"
        mkdir_code, mkdir_output = run_ssh(device, f"mkdir -p {shlex.quote(REMOTE_BASE)}", timeout_seconds=20)
        if mkdir_code != 0:
            print(mkdir_output.rstrip())
            return mkdir_code

        scp_code, scp_output = run_scp_to_device(device, local_model, remote_model)
        if scp_code != 0:
            print(scp_output.rstrip())
            return scp_code

    selected_python = python_bin or DEFAULT_PYTHON_TEMPLATE.format(user=device.user)
    command = (
        "cat > /tmp/edge-rknn-smoke.sh <<'SH'\n"
        f"{RKNN_SMOKE_SCRIPT}\n"
        "SH\n"
        "chmod +x /tmp/edge-rknn-smoke.sh\n"
        f"/tmp/edge-rknn-smoke.sh {shlex.quote(remote_model)} {shlex.quote(selected_python)}"
    )
    print(f"===== RKNN smoke {device.id} {asset.id} =====")
    code, output = run_ssh(device, command, timeout_seconds=90)
    if output:
        print(output.rstrip())
    return code
