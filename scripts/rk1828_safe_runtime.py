#!/usr/bin/env python3
"""Safely run one RK1828 runtime operation at a time on the RK3588 host."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import textwrap


DEFAULT_HOST = "192.168.1.52"
DEFAULT_USER = "orangepi"
DEFAULT_PASSWORD_ENV = "EDGE_ORANGE_RK3588_PASSWORD"
DEFAULT_MODULE = "/usr/lib/modules/pcie-rkep.ko"
DEFAULT_SOURCE_MODULE = ""
DEFAULT_DEVICE_ID = "0000:01:00.0"
DEFAULT_FIRMWARE = "/lib/firmware/rknn3_rk1820.img"
DEFAULT_VISION_DIR = "/home/orangepi/edge-model-lab/rk1828-vision-smoke"
DEFAULT_VISION_MODEL = "Qwen3-VL-4B-vision-rk1828-prune.rknn"
DEFAULT_VISION_WEIGHT = "Qwen3-VL-4B-vision-rk1828-prune.weight"
FIRMWARE_RISK_TOKEN = "ALLOW_RK1828_FIRMWARE_RISK"


REMOTE_SCRIPT = r"""#!/usr/bin/env bash
set -euo pipefail

action="${1:?missing action}"
device_id="${2:-0000:01:00.0}"
module_path="${3:-/usr/lib/modules/pcie-rkep.ko}"
firmware_path="${4:-/lib/firmware/rknn3_rk1820.img}"
vision_dir="${5:-/home/orangepi/edge-model-lab/rk1828-vision-smoke}"
vision_model="${6:-Qwen3-VL-4B-vision-rk1828-prune.rknn}"
vision_weight="${7:-Qwen3-VL-4B-vision-rk1828-prune.weight}"
source_module="${8:-}"
firmware_risk_token="${9:-}"

lock_file=/tmp/rk1828-runtime.lock
exec 9>"$lock_file"
if ! flock -n 9; then
  echo "refusing: another rk1828_safe_runtime operation already holds $lock_file" >&2
  exit 80
fi

run_timeout() {
  local seconds="$1"
  shift
  timeout --foreground "$seconds" "$@"
}

print_processes() {
  ps -eo pid,ppid,stat,etime,cmd |
    grep -E 'rknn3_transfer_proxy|pcie_upgrade_tool|rknn3_model_test|rknn3_vlm_demo|rknn3_llm_demo|rkllm3-server' |
    grep -v grep || true
}

has_process() {
  pgrep -f "$1" >/dev/null 2>&1
}

refuse_if_upgrade_or_model_running() {
  if has_process 'pcie_upgrade_tool|rknn3_model_test|rknn3_vlm_demo|rknn3_llm_demo|rkllm3-server'; then
    echo "refusing: RK1828 upgrade/model process is already running" >&2
    print_processes >&2
    exit 81
  fi
}

refuse_if_proxy_running() {
  if has_process 'rknn3_transfer_proxy'; then
    echo "refusing: rknn3_transfer_proxy is running; stop it before firmware/update operations" >&2
    print_processes >&2
    exit 82
  fi
}

status() {
  echo "=== host ==="
  hostname
  uptime
  who -b || true

  echo "=== pci ==="
  lspci -nn | grep -Ei '182a|1828|processing' || true

  echo "=== driver ==="
  lsmod | grep -E '^pcie_rkep|rkep' || true
  ls -l "$module_path" 2>&1 || true
  ls -l /dev/pcie-rkep-* 2>&1 || true

  echo "=== runtime processes ==="
  print_processes

  echo "=== services ==="
  systemctl is-active rknn3.service rknn-mdns.service 2>&1 || true
  systemctl is-enabled rknn3.service rknn-mdns.service 2>&1 || true

  echo "=== recent rk1828 log ==="
  dmesg -T | grep -Ei 'fe150000|182a|rkep|rknn|pcie' | tail -80 || true
}

devices() {
  refuse_if_upgrade_or_model_running
  echo "=== transfer devices ==="
  if ! command -v /bin/rknn3_transfer_proxy >/dev/null 2>&1; then
    echo "missing /bin/rknn3_transfer_proxy" >&2
    exit 88
  fi
  run_timeout 10 /bin/rknn3_transfer_proxy devices
}

stop_runtime() {
  echo "=== stopping runtime processes ==="
  pkill -TERM -f 'rknn3_transfer_proxy|pcie_upgrade_tool|rknn3_model_test|rknn3_vlm_demo|rknn3_llm_demo|rkllm3-server' 2>/dev/null || true
  sleep 2
  pkill -KILL -f 'rknn3_transfer_proxy|pcie_upgrade_tool|rknn3_model_test|rknn3_vlm_demo|rknn3_llm_demo|rkllm3-server' 2>/dev/null || true
  print_processes
}

load_driver() {
  refuse_if_upgrade_or_model_running
  echo "=== loading driver ==="
  if lsmod | grep -q '^pcie_rkep'; then
    echo "pcie_rkep already loaded"
  else
    if [ ! -f "$module_path" ]; then
      echo "missing module: $module_path" >&2
      exit 83
    fi
    insmod "$module_path"
  fi
  lsmod | grep -E '^pcie_rkep|rkep' || true
  ls -l /dev/pcie-rkep-* 2>&1 || true
}

unload_driver() {
  refuse_if_upgrade_or_model_running
  refuse_if_proxy_running
  echo "=== unloading driver ==="
  if lsmod | grep -q '^pcie_rkep'; then
    rmmod pcie_rkep
  else
    echo "pcie_rkep is not loaded"
  fi
  lsmod | grep -E '^pcie_rkep|rkep' || true
  ls -l /dev/pcie-rkep-* 2>&1 || true
}

install_module() {
  refuse_if_upgrade_or_model_running
  refuse_if_proxy_running
  if [ -z "$source_module" ]; then
    echo "missing --source-module for install-module" >&2
    exit 89
  fi
  if [ ! -f "$source_module" ]; then
    echo "missing source module: $source_module" >&2
    exit 90
  fi
  echo "=== installing module ==="
  if lsmod | grep -q '^pcie_rkep'; then
    rmmod pcie_rkep
  fi
  if [ -f "$module_path" ]; then
    cp -a "$module_path" "${module_path}.bak-$(date +%Y%m%d%H%M%S)"
  fi
  install -m 0644 "$source_module" "$module_path"
  modinfo "$module_path" | sed -n '1,40p'
}

firmware() {
  refuse_if_proxy_running
  refuse_if_upgrade_or_model_running
  if [ "$firmware_risk_token" != "ALLOW_RK1828_FIRMWARE_RISK" ]; then
    echo "refusing: firmware download has repeatedly made the RK3588 host unreachable" >&2
    echo "only run it with --allow-firmware-risk when physical power recovery is available" >&2
    exit 91
  fi
  echo "=== firmware download ==="
  if [ ! -f "$firmware_path" ]; then
    echo "missing firmware: $firmware_path" >&2
    exit 84
  fi
  if [ ! -e "/dev/pcie-rkep-${device_id}" ]; then
    echo "missing /dev/pcie-rkep-${device_id}; run load-driver first" >&2
    exit 85
  fi
  run_timeout 90 /bin/pcie_upgrade_tool -s "$device_id" uf "$firmware_path"
}

start_proxy() {
  refuse_if_upgrade_or_model_running
  echo "=== starting proxy ==="
  if has_process 'rknn3_transfer_proxy'; then
    echo "proxy already running"
  else
    rm -f /tmp/rknn3-transfer-proxy.log
    RKNN3_NETWORK_SOCKET_FILE=/tmp/rk-mdns.ini \
      nohup /bin/rknn3_transfer_proxy >/tmp/rknn3-transfer-proxy.log 2>&1 9>&- &
    sleep 3
  fi
  print_processes
  echo "=== proxy log ==="
  sed -n '1,120p' /tmp/rknn3-transfer-proxy.log 2>/dev/null || true
  echo "=== devices ==="
  run_timeout 10 /bin/rknn3_transfer_proxy devices 2>&1 || true
}

vision_smoke() {
  refuse_if_upgrade_or_model_running
  if ! has_process 'rknn3_transfer_proxy'; then
    echo "refusing: proxy is not running; run start-proxy first" >&2
    exit 86
  fi
  local model_path="$vision_dir/$vision_model"
  local weight_path="$vision_dir/$vision_weight"
  if [ ! -f "$model_path" ] || [ ! -f "$weight_path" ]; then
    echo "missing vision smoke files under $vision_dir" >&2
    ls -l "$vision_dir" 2>&1 || true
    exit 87
  fi
  echo "=== vision model smoke ==="
  cd "$vision_dir"
  run_timeout 180 /bin/rknn3_model_test "$vision_model" "$vision_weight" none none 0x3 1
}

case "$action" in
  status) status ;;
  devices) devices ;;
  stop-runtime) stop_runtime ;;
  load-driver) load_driver ;;
  unload-driver) unload_driver ;;
  install-module) install_module ;;
  firmware) firmware ;;
  start-proxy) start_proxy ;;
  vision-smoke) vision_smoke ;;
  *)
    echo "unknown action: $action" >&2
    exit 64
    ;;
esac
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run guarded RK1828/RKNN3 operations on the RK3588 host."
    )
    parser.add_argument(
        "action",
        choices=(
            "status",
            "devices",
            "stop-runtime",
            "load-driver",
            "unload-driver",
            "install-module",
            "firmware",
            "start-proxy",
            "vision-smoke",
        ),
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--user", default=DEFAULT_USER)
    parser.add_argument("--port", default="22")
    parser.add_argument("--password-env", default=DEFAULT_PASSWORD_ENV)
    parser.add_argument("--device-id", default=DEFAULT_DEVICE_ID)
    parser.add_argument("--module-path", default=DEFAULT_MODULE)
    parser.add_argument("--source-module", default=DEFAULT_SOURCE_MODULE)
    parser.add_argument("--firmware-path", default=DEFAULT_FIRMWARE)
    parser.add_argument("--vision-dir", default=DEFAULT_VISION_DIR)
    parser.add_argument("--vision-model", default=DEFAULT_VISION_MODEL)
    parser.add_argument("--vision-weight", default=DEFAULT_VISION_WEIGHT)
    parser.add_argument(
        "--allow-firmware-risk",
        action="store_true",
        help=(
            "Allow the firmware action. This can make the RK3588 host "
            "unreachable and should only be used with physical recovery access."
        ),
    )
    return parser


def run_remote(args: argparse.Namespace) -> int:
    password = os.environ.get(args.password_env) or os.environ.get("SSHPASS")
    if not password:
        print(
            f"Set {args.password_env} or SSHPASS for SSH and sudo authentication.",
            file=sys.stderr,
        )
        return 2

    remote_args = [
        args.action,
        args.device_id,
        args.module_path,
        args.firmware_path,
        args.vision_dir,
        args.vision_model,
        args.vision_weight,
        args.source_module,
        FIRMWARE_RISK_TOKEN if args.allow_firmware_risk else "",
    ]
    remote_cmd = textwrap.dedent(
        f"""
        read -r sudo_password
        tmp=$(mktemp /tmp/rk1828-safe-runtime.XXXXXX.sh)
        cat > "$tmp"
        chmod 700 "$tmp"
        printf "%s\\n" "$sudo_password" | sudo -S -p "" bash "$tmp" {' '.join(shlex.quote(arg) for arg in remote_args)}
        rc=$?
        rm -f "$tmp"
        exit "$rc"
        """
    ).strip()

    ssh_cmd = [
        "sshpass",
        "-e",
        "ssh",
        "-o",
        "PreferredAuthentications=password",
        "-o",
        "PubkeyAuthentication=no",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "ConnectTimeout=8",
        "-p",
        str(args.port),
        f"{args.user}@{args.host}",
        remote_cmd,
    ]

    env = os.environ.copy()
    env["SSHPASS"] = password
    result = subprocess.run(
        ssh_cmd,
        input=f"{password}\n{REMOTE_SCRIPT}",
        text=True,
        env=env,
        check=False,
    )
    return result.returncode


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return run_remote(args)


if __name__ == "__main__":
    raise SystemExit(main())
