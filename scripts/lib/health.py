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
    code, output = run_ssh(device, "sh -s", timeout_seconds=35, stdin=HEALTH_SCRIPT)
    if code != 0:
        print(f"health check failed with exit code {code}")
    print(output.rstrip())
    print()
    return code
