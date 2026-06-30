from __future__ import annotations

from .config import Device
from .ssh import run_remote_sudo


DEFAULT_UNIT = "edge-rknn-yolo-smoke.service"


def print_service_status(device: Device, unit: str = DEFAULT_UNIT) -> int:
    command = (
        f"systemctl status --no-pager {unit}; "
        f"printf '\\n## show\\n'; "
        f"systemctl show {unit} -p ActiveState -p Result -p ExecMainStatus --no-pager"
    )
    print(f"===== service status {device.id} {unit} =====")
    code, output = run_remote_sudo(device, command, timeout_seconds=30)
    if output:
        print(output.rstrip())
    return code


def print_service_logs(device: Device, unit: str = DEFAULT_UNIT, lines: int = 80) -> int:
    command = f"journalctl -u {unit} -n {int(lines)} --no-pager"
    print(f"===== service logs {device.id} {unit} =====")
    code, output = run_remote_sudo(device, command, timeout_seconds=30)
    if output:
        print(output.rstrip())
    return code
