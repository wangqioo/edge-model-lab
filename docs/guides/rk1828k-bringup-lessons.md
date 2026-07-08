# RK1828K Bring-Up Lessons

This is the cleaned-up operating knowledge from the RK1828K debug session. It
keeps the useful conclusions and removes the dead ends from the chronological
experiment logs.

## Final Diagnosis

The RK1828K board, power, PCIe link, and `rknn3_rk1820.img` firmware path were
not the root cause.

The real blocker was the host-side `pcie-rkep.ko` driver. The vendor source was
close, but not directly compatible with the Orange Pi 5 Plus
`6.1.43-rockchip-rk3588` kernel and RKNN3 `1.0.4` userspace.

The working fix was an adapted vendor RKEP module:

```text
source: vendor rknn_install_without_model(1).tar.gz / rknn/driver/pcie-rkep
kernel tree: /home/wq/edge-tools/orangepi-kernel/linux-orangepi-6.1.43-full
kernel commit: 752c0d0a12fdce201da45852287b48382caa8c0f
DRV_VERSION: 0x00030301
disabled: PCIE_EP_RESET_CTRL external PM reset call missing from Orange Pi 6.1.43
kept: PCIE_EP_RESET_SLOT using rkep_ep_slot_reset()
module sha256: 58b4cd6664953d560aa8fc72b6295caec2634793ba17246f32e66108fcb913b2
installed: /usr/lib/modules/pcie-rkep.ko
backup: /root/pcie-rkep-before-vendor-adapted-20260708-133536.ko
```

After this driver was loaded, full firmware download succeeded and `rknn-smi`
reported the device online:

```text
Device 0 Status: Online
Health: OK
Chip Name: RK1828
Bus-Id: 0000:01:00.0
Memory: 32 / 5120 MB
```

## Useful Debug Sequence

Do not start with model tests. Bring the stack up in layers:

```text
12V power and PCIe enumeration
-> pcie-rkep driver and /dev node
-> pcie_upgrade_tool td
-> firmware download
-> rknn-smi Online
-> transfer proxy devices
-> model load/init
-> real inference
```

The important distinction is that PCIe enumeration is not enough. A broken RKEP
driver can still expose `/dev/pcie-rkep-*` while failing later during firmware
download or SMI/proxy interaction.

## Known Good Manual Bring-Up

This is now a recovery path, not the normal day-to-day path. The normal path is
the auto-start service in the next section.

Keep the vendor services disabled:

```bash
systemctl disable rknn3.service rknn-mdns.service
```

Manual sequence after a clean boot:

```bash
killall rknn3_transfer_proxy 2>/dev/null || true
killall pcie_upgrade_tool 2>/dev/null || true

rmmod pcie_rkep 2>/dev/null || true
insmod /usr/lib/modules/pcie-rkep.ko

pcie_upgrade_tool -s 0000:01:00.0 td
pcie_upgrade_tool -s 0000:01:00.0 uf /lib/firmware/rknn3_rk1820.img /tmp/rk1828-fw

RKNN3_NETWORK_SOCKET_FILE=/tmp/rk-mdns.ini \
  nohup /bin/rknn3_transfer_proxy >/tmp/rknn3-transfer-proxy.log 2>&1 &

rknn-smi info
rknn3_transfer_proxy devices
```

Expected working signs:

```text
pcie_upgrade_tool td:
  Soc=rk1820 Addr=0000:01:00.0 Mode=MaskROM [1d87:182a]
  Testing device OK

firmware:
  Downloading bootloader OK
  Running ddr code...OK
  Running subsoc_os code...OK
  Downloading firmware OK

rknn-smi:
  Status Online
  Chip Name RK1828
  Bus-Id 0000:01:00.0

proxy:
  0000:01:00.0 b98e6c51 PCIE
```

## Automatic Bring-Up

The working boot path is controlled by these files:

```text
repo source:
  deploy/systemd/rk1828/rk1828-runtime-start
  deploy/systemd/rk1828/rk1828-runtime.service

installed on RK3588 host:
  /usr/local/sbin/rk1828-runtime-start
  /etc/systemd/system/rk1828-runtime.service
```

Enabled services:

```bash
systemctl enable rk1828-rkep-load.service rk1828-runtime.service
systemctl disable rknn3.service rknn-mdns.service
```

Boot order:

```text
rk1828-rkep-load.service
-> load adapted /usr/lib/modules/pcie-rkep.ko
-> create /dev/pcie-rkep-0000:01:00.0
-> rk1828-runtime.service
-> verify adapted driver sha256
-> download /lib/firmware/rknn3_rk1820.img with pcie_upgrade_tool
-> exec /bin/rknn3_transfer_proxy in the systemd cgroup
```

The runtime script deliberately checks the adapted driver hash before touching
the RK1828K:

```text
58b4cd6664953d560aa8fc72b6295caec2634793ba17246f32e66108fcb913b2
```

This prevents a vendor reinstall from silently replacing the working driver
with an incompatible one.

Reboot verification on 2026-07-08:

```text
system boot: 2026-07-08 21:38 CST
rk1828-runtime.service: active (running), enabled
rknn3.service: disabled, inactive
rknn-mdns.service: disabled, inactive
rknn-smi: Device 0 Online, Health OK, Chip RK1828, Bus-Id 0000:01:00.0
memory: 32 / 5120 MB
proxy: 0000:01:00.0 b98e6c51 PCIE
```

Normal status checks:

```bash
systemctl status rk1828-runtime.service --no-pager -l
journalctl -u rk1828-runtime.service -n 120 --no-pager
rknn-smi info
rknn3_transfer_proxy devices
```

The existing guarded wrapper still works with the service running:

```bash
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py smi
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py devices
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py vision-smoke
```

`vision-smoke` is expected to end at `Failed to open input numpy file: none`;
the important proof is before that:

```text
rknn3_init success
rknn3_load_model_from_data success
Core number: 8
rknn3_model_init success
```

## What Was Noise

These were useful to check once, but they were not the final cause:

```text
power supply capacity
startup sleep 2 / sleep 10
whether the connection is USB
whether PCIe enumeration exists
whether rknn3_rk1820.img contains RK1820 strings
whether explicit db BOOT is required before uf firmware
```

The firmware name and internal strings are confusing, but the image did work
once the host RKEP driver was corrected.

## What Actually Mattered

The vendor source had two critical compatibility issues:

1. `DRV_VERSION` was `0x00030300`, while RKNN3 userspace needed `0x30301`.
2. `PCIE_EP_RESET_CTRL` used a Rockchip PCIe PM reset API that is not present in
   the Orange Pi `6.1.43-rockchip-rk3588` tree.

The first issue made RKNN3 reject or mis-handle the driver ABI. The second issue
prevented compiling the vendor source against the matching Orange Pi kernel
tree.

After adapting those two points, the driver could load and firmware download no
longer wedged the host.

## Model Deployment Notes

Future model deployments should not hit the old device-offline problem as long
as the adapted RKEP module is loaded and firmware has been downloaded.

New model failures are more likely to be normal RKNN3/model issues:

```text
wrong core mask
wrong input shape
wrong dtype
unsupported ops
model too large for node memory
bad or incompatible RKNN3 conversion artifacts
test-tool input format problems
```

RK1828 reports 8 cores. Use `0xff` as the all-core mask. The earlier `0x3`
mask was wrong for this device:

```text
Core number: 8
Error: core_mask 0x3 does not match core number 8
```

Known model-load proof from the Qwen3-VL vision smoke:

```text
rknn3_init success
rknn3_load_model_from_data success
Core number: 8
rknn3_model_init success
```

The `rknn3_model_test` `.npy` reader is picky. A failure like this is a test
input parser problem, not a hardware bring-up failure:

```text
Invalid numpy dtype f2
```

## Do Not Repeat

Avoid these patterns:

```text
running firmware download while proxy/model processes are active
using pkill -f with broad patterns that can kill the current SSH command
trusting a vendor installer before reading what it overwrites
running driver-ubuntu.sh without matching kernel headers/source
enabling rknn3.service before manual reboot behavior is validated
assuming /dev/pcie-rkep-* means the full RKNN3 path is healthy
```

## If It Breaks Again

First recovery checks:

```bash
lspci -nn | grep -Ei '182a|1828|processing'
lsmod | grep pcie_rkep
ls -l /dev/pcie-rkep-*
sha256sum /usr/lib/modules/pcie-rkep.ko
modinfo /usr/lib/modules/pcie-rkep.ko | grep vermagic
pcie_upgrade_tool -s 0000:01:00.0 td
rknn-smi info
```

The expected installed module hash is:

```text
58b4cd6664953d560aa8fc72b6295caec2634793ba17246f32e66108fcb913b2
```

If the hash changed, restore the adapted module or rebuild it from the vendor
source with the two compatibility changes above.

## Source Logs

Keep the full chronology for audit only:

```text
docs/experiments/2026-07-03-rk1828-12v-power-detection.md
docs/experiments/2026-07-08-rk1828k-vendor-escalation.md
```
