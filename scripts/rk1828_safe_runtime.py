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
DEFAULT_DEVICE_ID = "0000:01:00.0"
DEFAULT_FIRMWARE = "/lib/firmware/rknn3_rk1820.img"
DEFAULT_BOOTLOADER = "/tmp/rk1828-fw/BOOT"
DEFAULT_VISION_DIR = "/home/orangepi/edge-model-lab/rk1828-vision-smoke"
DEFAULT_VISION_MODEL = "Qwen3-VL-4B-vision-rk1828-prune.rknn"
DEFAULT_VISION_WEIGHT = "Qwen3-VL-4B-vision-rk1828-prune.weight"


REMOTE_SCRIPT = r"""#!/usr/bin/env bash
set -euo pipefail

action="${1:?missing action}"
device_id="${2:-0000:01:00.0}"
module_path="${3:-/usr/lib/modules/pcie-rkep.ko}"
firmware_path="${4:-/lib/firmware/rknn3_rk1820.img}"
vision_dir="${5:-/home/orangepi/edge-model-lab/rk1828-vision-smoke}"
vision_model="${6:-Qwen3-VL-4B-vision-rk1828-prune.rknn}"
vision_weight="${7:-Qwen3-VL-4B-vision-rk1828-prune.weight}"
vendor_id="${8:-0}"
bootloader_path="${9:-/tmp/rk1828-fw/BOOT}"

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

kill_runtime_processes() {
  local signal="$1"
  local name
  for name in \
    rknn3_transfer_proxy \
    rknn3_transfer_proxy_b98e6c51 \
    pcie_upgrade_tool \
    rknn3_model_test \
    rknn3_vlm_demo \
    rknn3_llm_demo \
    rkllm3-server; do
    pidof "$name" 2>/dev/null | xargs -r kill "-$signal" 2>/dev/null || true
  done
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

post_recovery_report() {
  echo "=== post recovery report ==="
  date -Is

  echo "=== host ==="
  hostname
  uname -a
  uptime

  echo "=== pci ==="
  lspci -nn | grep -Ei '182a|1828|processing' || true
  if [ -e "/sys/bus/pci/devices/${device_id}/vendor" ]; then
    printf "%s " "$device_id"
    cat "/sys/bus/pci/devices/${device_id}/vendor" "/sys/bus/pci/devices/${device_id}/device" "/sys/bus/pci/devices/${device_id}/class" 2>/dev/null | tr '\n' ' '
    printf "\n"
  fi

  echo "=== driver ==="
  lsmod | grep -E '^pcie_rkep|rkep' || true
  modinfo "$module_path" 2>/dev/null | sed -n '1,80p' || true
  sha256sum "$module_path" 2>/dev/null || true
  ls -l /dev/pcie-rkep-* 2>&1 || true

  echo "=== firmware and userspace ==="
  sha256sum "$firmware_path" /bin/rknn-smi /bin/pcie_upgrade_tool /bin/rknn3_transfer_proxy 2>/dev/null || true
  ls -l "$firmware_path" /bin/rknn-smi /bin/pcie_upgrade_tool /bin/rknn3_transfer_proxy 2>/dev/null || true

  echo "=== runtime processes ==="
  print_processes

  echo "=== services ==="
  systemctl is-active rknn3.service rknn-mdns.service 2>&1 || true
  systemctl is-enabled rknn3.service rknn-mdns.service 2>&1 || true

  echo "=== rknn-smi detailed ==="
  RKNN_LOG_LEVEL=DEBUG run_timeout 15 /bin/rknn-smi info -l 2>&1 || true

  echo "=== rknn-smi table ==="
  run_timeout 15 /bin/rknn-smi info 2>&1 || true

  echo "=== rknn-smi log ==="
  tail -120 /var/log/rknn-smi.log 2>/dev/null || true

  echo "=== recent rk1828 kernel log ==="
  dmesg -T | grep -Ei 'fe150000|182a|rkep|rknn|pcie' | tail -120 || true
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
  kill_runtime_processes TERM
  sleep 2
  kill_runtime_processes KILL
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
    sleep 2  # wait for /dev/pcie-rkep-* after insmod
  fi
  lsmod | grep -E '^pcie_rkep|rkep' || true
  ls -l /dev/pcie-rkep-* 2>&1 || true
}

install_driver_service() {
  refuse_if_upgrade_or_model_running
  echo "=== installing rk1828 RKEP driver service ==="
  if [ ! -f "$module_path" ]; then
    echo "missing module: $module_path" >&2
    exit 83
  fi
  install -d /usr/local/sbin
  cat > /usr/local/sbin/rk1828-rkep-load <<EOF
#!/usr/bin/env bash
set -euo pipefail

module_path="$module_path"
device_id="$device_id"

echo 1 > /sys/bus/pci/rescan || true
if ! lsmod | grep -q '^pcie_rkep'; then
  insmod "\$module_path"
fi
sleep 2
ls -l "/dev/pcie-rkep-\$device_id"
EOF
  chmod 755 /usr/local/sbin/rk1828-rkep-load

  cat > /etc/systemd/system/rk1828-rkep-load.service <<'EOF'
[Unit]
Description=Load RK1828 RKEP PCIe driver
After=systemd-udev-settle.service
Wants=systemd-udev-settle.service
ConditionPathExists=/usr/lib/modules/pcie-rkep.ko

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/rk1828-rkep-load
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable rk1828-rkep-load.service
  systemctl restart rk1828-rkep-load.service
  systemctl --no-pager --full status rk1828-rkep-load.service || true
  lsmod | grep -E '^pcie_rkep|rkep' || true
  ls -l /dev/pcie-rkep-* 2>&1 || true
}

firmware() {
  refuse_if_upgrade_or_model_running
  echo "=== firmware download ==="
  if ! has_process 'rknn3_transfer_proxy'; then
    echo "refusing: proxy is not running; run start-proxy first" >&2
    exit 89
  fi
  if [ ! -f "$firmware_path" ]; then
    echo "missing firmware: $firmware_path" >&2
    exit 84
  fi
  if [ ! -e "/dev/pcie-rkep-${device_id}" ]; then
    echo "missing /dev/pcie-rkep-${device_id}; run load-driver first" >&2
    exit 85
  fi
  run_timeout 45 /bin/pcie_upgrade_tool -s "$device_id" uf "$firmware_path"
  sleep 10  # wait for RK1828 after firmware download
}

firmware_direct() {
  refuse_if_upgrade_or_model_running
  refuse_if_proxy_running
  echo "=== direct firmware download without proxy ==="
  if [ ! -f "$firmware_path" ]; then
    echo "missing firmware: $firmware_path" >&2
    exit 84
  fi
  if [ ! -e "/dev/pcie-rkep-${device_id}" ]; then
    echo "missing /dev/pcie-rkep-${device_id}; run load-driver first" >&2
    exit 85
  fi
  mkdir -p /tmp/rk1828-fw
  rm -f /tmp/rk1828-fw/loader.bin
  run_timeout 20 /bin/pcie_upgrade_tool -s "$device_id" td
  run_timeout 60 /bin/pcie_upgrade_tool -s "$device_id" uf "$firmware_path" /tmp/rk1828-fw
  sleep 10  # wait for RK1828 after firmware download
}

test_device() {
  refuse_if_upgrade_or_model_running
  echo "=== pcie upgrade test-device ==="
  if [ ! -e "/dev/pcie-rkep-${device_id}" ]; then
    echo "missing /dev/pcie-rkep-${device_id}; run load-driver first" >&2
    exit 85
  fi
  run_timeout 20 /bin/pcie_upgrade_tool -s "$device_id" td
}

read_vendor() {
  refuse_if_upgrade_or_model_running
  echo "=== pcie upgrade read-vendor id=${vendor_id} ==="
  if [ ! -e "/dev/pcie-rkep-${device_id}" ]; then
    echo "missing /dev/pcie-rkep-${device_id}; run load-driver first" >&2
    exit 85
  fi
  run_timeout 20 /bin/pcie_upgrade_tool -s "$device_id" rvd "$vendor_id"
}

reset_device() {
  refuse_if_upgrade_or_model_running
  refuse_if_proxy_running
  echo "=== pcie upgrade reset-device ==="
  if [ ! -e "/dev/pcie-rkep-${device_id}" ]; then
    echo "missing /dev/pcie-rkep-${device_id}; run load-driver first" >&2
    exit 85
  fi
  run_timeout 20 /bin/pcie_upgrade_tool -s "$device_id" rd
  sleep 3
  run_timeout 20 /bin/pcie_upgrade_tool -s "$device_id" td
}

bootloader_direct() {
  refuse_if_upgrade_or_model_running
  refuse_if_proxy_running
  echo "=== direct bootloader download without proxy ==="
  if [ ! -f "$bootloader_path" ]; then
    echo "missing bootloader: $bootloader_path" >&2
    exit 90
  fi
  if [ ! -e "/dev/pcie-rkep-${device_id}" ]; then
    echo "missing /dev/pcie-rkep-${device_id}; run load-driver first" >&2
    exit 85
  fi
  run_timeout 20 /bin/pcie_upgrade_tool -s "$device_id" td
  run_timeout 30 /bin/pcie_upgrade_tool -s "$device_id" db "$bootloader_path"
  sleep 3
  run_timeout 20 /bin/pcie_upgrade_tool -s "$device_id" td
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
  install-driver-service) install_driver_service ;;
  firmware) firmware ;;
  firmware-direct) firmware_direct ;;
  test-device) test_device ;;
  read-vendor) read_vendor ;;
  reset-device) reset_device ;;
  bootloader-direct) bootloader_direct ;;
  post-recovery-report) post_recovery_report ;;
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
            "install-driver-service",
            "firmware",
            "firmware-direct",
            "test-device",
            "read-vendor",
            "reset-device",
            "bootloader-direct",
            "post-recovery-report",
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
    parser.add_argument("--firmware-path", default=DEFAULT_FIRMWARE)
    parser.add_argument("--bootloader-path", default=DEFAULT_BOOTLOADER)
    parser.add_argument(
        "--allow-firmware-hang",
        action="store_true",
        help="Allow the firmware action, which has previously made the RK3588 host unreachable.",
    )
    parser.add_argument(
        "--allow-device-reset",
        action="store_true",
        help="Allow pcie_upgrade_tool rd, which resets the RK1828 endpoint.",
    )
    parser.add_argument(
        "--allow-bootloader-download",
        action="store_true",
        help="Allow pcie_upgrade_tool db, which may make the RK3588 host unreachable.",
    )
    parser.add_argument(
        "--allow-loader-interaction",
        action="store_true",
        help="Allow Loader-state pcie_upgrade_tool interactions such as rvd.",
    )
    parser.add_argument(
        "--vendor-id",
        default="0",
        help="Vendor entry id for the read-vendor action.",
    )
    parser.add_argument("--vision-dir", default=DEFAULT_VISION_DIR)
    parser.add_argument("--vision-model", default=DEFAULT_VISION_MODEL)
    parser.add_argument("--vision-weight", default=DEFAULT_VISION_WEIGHT)
    return parser


def run_remote(args: argparse.Namespace) -> int:
    if args.action in {"firmware", "firmware-direct"} and not args.allow_firmware_hang:
        print(
            f"Refusing {args.action} action: previous pcie_upgrade_tool uf attempts made "
            "the RK3588 host unreachable. Re-run with --allow-firmware-hang only "
            "when serial/local recovery is ready.",
            file=sys.stderr,
        )
        return 3
    if args.action == "reset-device" and not args.allow_device_reset:
        print(
            "Refusing reset-device action: pcie_upgrade_tool rd resets the RK1828 "
            "endpoint. Re-run with --allow-device-reset only when recovery is ready.",
            file=sys.stderr,
        )
        return 4
    if args.action == "bootloader-direct" and not args.allow_bootloader_download:
        print(
            "Refusing bootloader-direct action: previous loader/firmware download "
            "attempts made the RK3588 host unreachable. Re-run with "
            "--allow-bootloader-download only when recovery is ready.",
            file=sys.stderr,
        )
        return 5
    if args.action == "read-vendor" and not args.allow_loader_interaction:
        print(
            "Refusing read-vendor action: Loader-state rvd interaction has made "
            "the RK3588 host unreachable. Re-run with --allow-loader-interaction "
            "only when recovery is ready.",
            file=sys.stderr,
        )
        return 6

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
        args.vendor_id,
        args.bootloader_path,
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
