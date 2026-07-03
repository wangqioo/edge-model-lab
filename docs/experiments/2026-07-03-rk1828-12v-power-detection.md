# RK1828 12V Power Detection Check

## Goal

Check whether the RK1828 M.2 accelerator is visible to the RK3588 host after
separate 12V power was connected.

## Target

```text
orange-rk3588
orangepi@150.158.146.192:6280
```

## Time

```text
2026-07-03 00:52 CST
```

The RK3588 host had recently booted:

```text
orangepi5plus
Linux orangepi5plus 6.1.43-rockchip-rk3588
up 3 min
```

## PCIe Detection

`lspci -nn` only showed the built-in RK3588 PCIe bridges, Wi-Fi, and two
Realtek 2.5GbE controllers:

```text
0002:20:00.0 PCI bridge [0604]: Rockchip Electronics Co., Ltd RK3588 [1d87:3588]
0002:21:00.0 Network controller [0280]: Realtek RTL8852BE [10ec:b852]
0003:30:00.0 PCI bridge [0604]: Rockchip Electronics Co., Ltd RK3588 [1d87:3588]
0003:31:00.0 Ethernet controller [0200]: Realtek RTL8125 [10ec:8125]
0004:40:00.0 PCI bridge [0604]: Rockchip Electronics Co., Ltd RK3588 [1d87:3588]
0004:41:00.0 Ethernet controller [0200]: Realtek RTL8125 [10ec:8125]
```

There was no RK1828 or RK1820 endpoint.

`/sys/bus/pci/rescan` did not add any new PCIe device.

## Kernel Log

The likely M.2 PCIe controller is `fe150000.pcie`. It failed link training:

```text
rk-pcie fe150000.pcie: PCIe Linking... LTSSM is 0x0
rk-pcie fe150000.pcie: PCIe Linking... LTSSM is 0x1
rk-pcie fe150000.pcie: PCIe Link Fail, LTSSM is 0x0, hw_retries=0
rk-pcie fe150000.pcie: failed to initialize host
```

The other PCIe controllers linked successfully to known onboard devices.

## Runtime Check

RKNN3 runtime files are installed:

```text
/usr/local/bin/rkllm3-server
/usr/local/bin/rknn3_transfer_proxy
/home/orangepi/rknn3-runtime_v1.0.4.tar.gz
```

`rkllm3-server` reports:

```text
version: 1.0.4 (04c8fbc@2026-05-13T15:14:35)
```

`rknn3_transfer_proxy` starts its local control listener, but no RK1828 PCIe
device is visible:

```text
Starting RKNN3 Transfer Proxy DeviceManager (hybrid mode), Transfer version 1.0.4
ctrl: listening on 127.0.0.1:18898
DeviceManager: polling mode started
DeviceManager: polling mode exited
```

`rknn-smi` was not present in the installed runtime tree.

## Second Boot With RK1828 Powered First

After changing the power sequence so the RK1828 12V supply was on before the
RK3588 host booted, the PCIe link came up.

Detection time:

```text
2026-07-03 00:57 CST
```

`lspci -nn` now shows the RK1828 endpoint:

```text
0000:00:00.0 PCI bridge [0604]: Rockchip Electronics Co., Ltd RK3588 [1d87:3588] (rev 01)
0000:01:00.0 Processing accelerators [1200]: Rockchip Electronics Co., Ltd Device [1d87:182a] (rev 01)
```

The sysfs IDs are:

```text
0000:01:00.0 0x1d87 0x182a 0x120000
```

Kernel log:

```text
rk-pcie fe150000.pcie: PCIe Link up, LTSSM is 0x130011
rk-pcie fe150000.pcie: PCIe Gen.2 x1 link up
pci 0000:01:00.0: [1d87:182a] type 00 class 0x120000
```

## Corrected Power Timing

Later testing refined the power sequence. It is not enough for RK1828 12V to be
applied before RK3588 boot. The RK1828 board must be given time to complete its
own startup before RK3588 is powered on.

Observed corrected sequence:

```text
1. RK3588 off.
2. RK1828 12V on.
3. Wait until RK1828 appears fully started and physically stable.
4. Power on RK3588.
```

Verification time:

```text
2026-07-03 04:20 CST
```

`lspci -nn` on RK3588:

```text
0000:01:00.0 Processing accelerators [1200]: Rockchip Electronics Co., Ltd Device [1d87:182a] (rev 01)
```

Kernel log:

```text
rk-pcie fe150000.pcie: PCIe Link up, LTSSM is 0x130011
rk-pcie fe150000.pcie: PCIe Gen.2 x1 link up
pci 0000:01:00.0: [1d87:182a] type 00 class 0x120000
```

This explains the earlier inconsistent boot behavior: if RK3588 starts while
RK1828 is still in its own power-on transition, the host can fail or appear
stuck even though the nominal order was "RK1828 before RK3588". The operational
rule is now stricter: wait for RK1828 startup completion before RK3588 power-on.

`rknn3_transfer_proxy` also discovers the device and starts a per-device proxy:

```text
DeviceManager: started proxy pid=2415 for device=0000:01:00.0
Starting RKNN3 Transfer Proxy ... devid = 0000:01:00.0
ctrl: listening on 127.0.0.1:18821
DeviceManager: stopped proxy pid=2415 for device=0000:01:00.0
```

The stop above was expected because the proxy was run under a short `timeout`
probe.

Board-side artifact check:

```text
/home/orangepi/edge-model-lab/qwen3-vl-rk3588/models/qwen3-vl_vision_rk3588.rknn
/home/orangepi/edge-model-lab/qwen35-4b-rk3588/models/qwen3.5_vision_rk3588.rknn
```

## Runtime Smoke Attempt

The full RK1828 Qwen3-VL bundle is too large to move over the current FRP link
quickly, so a vision-only smoke bundle was staged first:

```text
/home/orangepi/edge-model-lab/rk1828-vision-smoke
```

The copied files matched the home-server hashes:

```text
33de410ff5299f49ff2558a8d652419c8316e59a0586fcf6391c7575e7cb2530  Qwen3-VL-4B-vision-rk1828-prune.rknn
ec4c3ea71c223a511ed4a772ecbeb2b85fcad1e6b779c298868ab1dd8f0fd7a0  Qwen3-VL-4B-vision-rk1828-prune.weight
```

A minimal C smoke program was compiled on RK3588 against:

```text
/opt/edge/rknn3-runtime-1.0.4/rknn3-runtime/rknn3-api/include
/opt/edge/rknn3-runtime-1.0.4/rknn3-runtime/rknn3-api/Linux/aarch64
```

Without `rknn3_transfer_proxy`, RKNN3 could not discover a device:

```text
find_devices ret=0 n_devices=0
init device=0000:01:00.0 ret=-10 ctx=0
```

With `rknn3_transfer_proxy` running, the API could discover the RK1828 PCIe
endpoint:

```text
find_devices ret=0 n_devices=1
device[0] id=0000:01:00.0 type=PCIE
```

However, initializing the device still failed:

```text
E NPUTransfer: Retry open failed, result = -1
E RKNNAPI: rknn3_init, server connect fail! ret = -1(ERROR_IO)
init device=0000:01:00.0 ret=-10 ctx=0
```

The proxy-side failure was:

```text
E NPUTransfer: rk_pcie_device_init failed, bus: 0000:01:00.0!
E NPUTransfer: Transfer interface open failed!, PCIE: 0000:01:00.0, name = Gongga
E NPUTransfer: Create client failed!, ret = -1
```

Running the proxy as root and manually enabling PCIe memory and bus mastering
changed the PCIe command register from disabled to enabled:

```text
Control: I/O- Mem- BusMaster-
Control: I/O- Mem+ BusMaster+
```

That was not sufficient. The same RKNN3 init failure remained.

## Host Kernel Blocker

The RK3588 host is currently running:

```text
Linux orangepi5plus 6.1.43-rockchip-rk3588 #1.0.8
```

Its kernel config does not include the Rockchip PCIe endpoint transfer support
needed by the RKNN3 proxy:

```text
# CONFIG_PCIE_FUNC_RKEP is not set
# CONFIG_NTB is not set
# CONFIG_UIO is not set
# CONFIG_VFIO is not set
```

The installed `rknn3_transfer_proxy` binary contains the diagnostic string:

```text
open rkep: %s fail, %s . kernel need config CONFIG_PCIE_FUNC_RKEP=y
```

This makes the current blocker host-kernel support, not model conversion and not
artifact integrity. The hardware is visible on PCIe, but the RKNN3 runtime cannot
open the RK1828 PCIe transfer path on this Orange Pi kernel.

## Driver Source Follow-Up

The RK1828 local materials do contain the driver installation clue, but it is in
the ASR guide rather than the main Qwen runbook material:

```text
/Users/wq/Downloads/开发资料/05_RKNN3软件SDK_V1.0.4/05_ASR使用指导/rk1.0.4版本中asr使用指导.pdf
cd pcie-rkep
make
scp ./pcie-rkep.ko /usr/lib/modules/pcie-rkep.ko
tar -zxvf rknn3_rk182x_m2_installer_arm64.tgz && bash install.sh && sync
```

The Lenovo release package for RK1820/RK1828 M.2 was downloaded and inspected.
It provides RKNN3 user-space binaries, services, firmware, and tools, but not
`pcie-rkep.ko`.

The RK3588 EVB10 release rootfs does contain the module:

```text
/usr/lib/modules/pcie-rkep.ko
name: pcie_rkep
description: Rockchip pcie-rkep demo function driver
vermagic: 6.1.162 SMP mod_unload aarch64
```

That module is not compatible with the current Orange Pi kernel:

```text
Orange Pi host: 6.1.43-rockchip-rk3588
EVB10 module:   6.1.162
```

The matching source path was found in Orange Pi/Rockchip kernel trees:

```text
drivers/misc/rockchip/pcie-rkep.c
drivers/pci/controller/dwc/pcie-dw-dmatest.c
```

Orange Pi build commit `55155f1d73cca3cf6bf42a03d7d16df2b14e8014` matches
`orangepi5plus` `REVISION="1.0.8"` and points at kernel branch
`orange-pi-6.1-rk35xx`. Kernel commit
`752c0d0a12fdce201da45852287b48382caa8c0f` is a 2024-02-03 `6.1.43`
candidate on that branch.

## RKEP Module Build And Load

After switching to LAN access, the full Orange Pi kernel checkout completed on
the home server:

```text
/home/wq/edge-tools/orangepi-kernel/linux-orangepi-6.1.43-full
git commit: 752c0d0a12fdce201da45852287b48382caa8c0f
Makefile: VERSION=6 PATCHLEVEL=1 SUBLEVEL=43
```

The RK3588 host config was copied from:

```text
/boot/config-6.1.43-rockchip-rk3588
```

Build adjustments:

```text
CONFIG_LOCALVERSION="-rockchip-rk3588"
# CONFIG_LOCALVERSION_AUTO is not set
CONFIG_PCIE_DW_DMATEST=y
CONFIG_PCIE_FUNC_RKEP=m
```

The Orange Pi 6.1.43 `pcie-rkep.c` needed two RK1828-specific changes compared
with the newer Rockchip 6.1 source:

```text
MODULE_DEVICE_TABLE(pcie_rkep, pcie_rkep_pcidev_id);
```

was changed to:

```text
MODULE_DEVICE_TABLE(pci, pcie_rkep_pcidev_id);
```

and the RK1828 PCI device ID was added:

```text
{ PCI_VDEVICE(ROCKCHIP, 0x182a), 1,  },
```

## RKNN3 1.0.4 RKEP ABI Patch

After the initial module loaded, `rknn3_transfer_proxy` still failed during
device open:

```text
pcie_rkep drv version 0x0 is not compatible, at least 0x30300
mmap index 7 is out of number
mmap index 8 is out of number
```

Binary inspection of `rknn3_transfer_proxy` showed the driver version is read
with:

```text
ioctl(fd, 0x80045000, &version)  # _IOR('P', 0, int)
```

The EVB10 `6.1.162` module strings showed BAR1/BAR5 mmap support, while the
Orange Pi 6.1.43 source only exposed BAR0/BAR2/BAR4 and resource indexes 0..6.

The local Orange Pi 6.1.43 source was patched to add:

```text
#define RKEP_FUNC_DRV_VERSION 0x30300
#define PCIE_EP_GET_FUNC_DRV_VERSION _IOR(PCIE_BASE, 0, int)
PCIE_EP_MMAP_RESOURCE_BAR1  # index 7
PCIE_EP_MMAP_RESOURCE_BAR5  # index 8
```

and `pcie-rkep.c` was patched to return `0x30300` for the version ioctl and mmap
BAR1/BAR5.

Rebuilt module metadata:

```text
name:     pcie_rkep
alias:    pci:v00001D87d0000182Asv*sd*bc*sc*i*
vermagic: 6.1.43-rockchip-rk3588 SMP mod_unload aarch64
```

After installing this module on RK3588:

```text
/usr/lib/modules/pcie-rkep.ko size: 209432
/dev/pcie-rkep-0000:01:00.0 present
```

`rknn3_transfer_proxy devices` returned:

```text
List of ntb devices attached
0000:01:00.0        b98e6c51    PCIE
```

`rknn3_transfer_proxy` then opened the device successfully:

```text
rk pcie tiny version: 30300
bar0 size=0x400000
bar1 size=0x100000
bar2 size=0x4000000
bar4 size=0x100000
bar5 size=0x100000
rc_cc_version=30300
gen2x1
```

This proves the host-driver ABI blocker was removed.

## Current Runtime Blocker

The converted vision smoke bundle is staged at:

```text
/home/orangepi/edge-model-lab/rk1828-vision-smoke
Qwen3-VL-4B-vision-rk1828-prune.rknn
Qwen3-VL-4B-vision-rk1828-prune.weight
```

The official test command:

```bash
/bin/rknn3_model_test Qwen3-VL-4B-vision-rk1828-prune.rknn \
  Qwen3-VL-4B-vision-rk1828-prune.weight none none 0x3 1
```

timed out after 180 seconds without model output.

A minimal line-buffered smoke program narrowed the hang:

```text
find_devices ret=0 n_devices=1
device[0] id=0000:01:00.0 type=PCIE
```

It then hung inside `rknn3_init` and timed out after 60 seconds. Therefore the
current blocker is RKNN3 device/server initialization, not PCIe enumeration, not
RKEP device open, and not model file loading.

## Firmware Download Risk

After stopping proxy/model processes, the guarded wrapper attempted:

```bash
/bin/pcie_upgrade_tool -s 0000:01:00.0 uf /lib/firmware/rknn3_rk1820.img
```

The command produced no progress output, did not return within the expected
window, and the RK3588 LAN SSH endpoint became unreachable:

```text
ssh: connect to host 192.168.1.52 port 22: Host is down
ssh: connect to host 192.168.1.52 port 22: Operation timed out
```

Do not run firmware download again unless physical recovery is available. The
safe wrapper now refuses `firmware` by default and requires:

```bash
./scripts/rk1828_safe_runtime.py firmware --allow-firmware-risk
```

After the board is physically recovered, the first command must be:

```bash
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py status
```

The rebuilt module reports:

```text
alias:    pci:v00001D87d0000182Asv*sd*bc*sc*i*
alias:    pci:v00001D87d0000356Asv*sd*bc*sc*i*
vermagic: 6.1.43-rockchip-rk3588 SMP mod_unload aarch64
```

It was installed to the RK3588 host:

```text
/usr/lib/modules/pcie-rkep.ko
```

Manual load succeeded:

```text
insmod_rc=0
crw------- 1 root root 10, 120 /dev/pcie-rkep-0000:01:00.0
/sys/bus/pci/drivers/pcie-rkep
```

Kernel log after load:

```text
pcie-rkep 0000:01:00.0: success to request msi irq
pcie-rkep 0000:01:00.0: vid=1d87
pcie-rkep 0000:01:00.0: did=182a
pcie-rkep 0000:01:00.0: obj_info magic=18, ver=49d76a9c
```

The RKNN3 M.2 installer was then installed from:

```text
/tmp/rknn3_rk182x_m2_installer_arm64.tgz
```

It installed `/bin/rknn-smi`, `/bin/rknn3_transfer_proxy`,
`/bin/rknn3_startup`, `/lib/librknn3_api.so`, firmware, udev rules, and the
`rknn3.service` unit. When `systemctl restart rknn3.service` was attempted, the
SSH session hung and the RK3588 host stopped responding on the LAN:

```text
ping 192.168.1.52: 100% packet loss
nc 192.168.1.52 22: Host is down / timed out
```

The host-kernel RKEP device-node problem is resolved, but RKNN3 startup is not
yet validated. On the next boot, inspect or disable `rknn3.service` before
starting it again.

## Reboot Follow-Up

After the RK3588 host was physically restarted, it still did not return on the
previous LAN address:

```text
ping 192.168.1.52: 100% packet loss
nc 192.168.1.52 22: Host is down / timed out
```

A LAN SSH scan did not find a new `orangepi5plus` target. The FRP port
`150.158.146.192:6280` accepted TCP, but SSH closed during login:

```text
Connection closed by 150.158.146.192 port 6280
```

Because the RKNN3 installer enabled `rknn3.service`, the likely next recovery
step is to boot the RK3588 with RK1828 power removed, or otherwise reach local
console, then disable the service before another remote test:

```bash
sudo systemctl disable --now rknn3.service
sudo systemctl disable --now rknn-mdns.service
```

After SSH is stable again, continue with manual one-step checks instead of
starting the service:

```bash
sudo insmod /usr/lib/modules/pcie-rkep.ko
ls -l /dev/pcie-rkep-*
/bin/rknn-smi info
/bin/rknn3_transfer_proxy devices
```

## Recovery With RK1828 Power Removed

The RK3588 host recovered when booted without RK1828 12V power:

```text
orangepi5plus
03:30:52 up 0 min
6.1.43-rockchip-rk3588
```

LAN SSH was available again at:

```text
orangepi@192.168.1.52:22
```

The RKNN3 services were disabled so they will not run during early boot:

```text
rknn3.service: disabled, inactive
rknn-mdns.service: disabled, inactive
```

The boot log with RK1828 unpowered showed the expected M.2 PCIe link failure:

```text
rk-pcie fe150000.pcie: PCIe Link Fail, LTSSM is 0x0, hw_retries=0
rk-pcie fe150000.pcie: failed to initialize host
rknn3_startup: Failed to load driver or find device
```

This supports the working hypothesis: RK3588 itself boots normally; the previous
hang occurs only when RK1828 is powered and RKNN3 startup proceeds into the
RK1828 PCIe/firmware path. Future tests must keep `rknn3.service` disabled and
run each step manually.

## RKNN3 Runtime Isolation Rollback

The RK1828/RKNN3 installer and custom RKEP module were treated as suspect after
the RK3588 host became unreachable when RK1828 was powered before RK3588 boot.
The following files installed or added during bring-up were moved out of the
live system paths instead of being deleted:

```text
/usr/lib/modules/pcie-rkep.ko
/bin/rknn3_startup
/bin/rknn3_transfer_proxy
/bin/rknn-smi
/bin/pcie_upgrade_tool
/bin/rknn3_session_test
/bin/rknn3_model_test
/bin/rknn3_cnn_demo
/bin/rknn3_vlm_demo
/bin/rknn3_llm_demo
/bin/rknn-console
/bin/rknn-mdns
/bin/rknn_upgrade_tool
/bin/pcie_speed_test_rc
/bin/rkllm3-server
/bin/upgrade_tool
/bin/rknn3_usb_startup.sh
/bin/rknn3_audio_encoder_test
/lib/firmware/rknn3_rk1820.img
/lib/librknn3_api.so
/lib/librknn3_api_rkcp.so
/lib/librknnsmi.so
/lib/libgstrknnutils.so
/lib/libmobilenetpostprocess.so
/lib/libresnetpostprocess.so
/lib/libyolov5spostprocess.so
/lib/libyolov6spostprocess.so
/lib/libyolov8spostprocess.so
/lib/aarch64-linux-gnu/gstreamer-1.0/libgstrknn.so
/lib/systemd/system/rknn3.service
/lib/systemd/system/rknn-mdns.service
/etc/udev/rules.d/75-rknn3-coprocessor.rules
/etc/profile.d/rknn3-env.sh
/userdata/aicp_test_aarch64
```

Backup location on the RK3588 host:

```text
/home/orangepi/rk1828-rknn3-runtime-disabled-20260703-034331
```

Post-rollback verification:

```text
rknn3.service: Failed to get unit file state: No such file or directory
rknn3.service: inactive
rknn-mdns.service: inactive
/usr/lib/modules/pcie-rkep.ko: absent
pcie_rkep loaded modules: 0
```

After the rollback, the RK3588 host was rebooted with RK1828 unpowered and came
back normally on LAN SSH:

```text
orangepi5plus
Linux orangepi5plus 6.1.43-rockchip-rk3588
03:44:10 up 0 min
```

The boot log no longer shows RKNN3 service startup or `pcie_rkep` module load.
It only shows the expected M.2 PCIe link failure while RK1828 is not powered:

```text
rk-pcie fe150000.pcie: PCIe Link Fail, LTSSM is 0x0, hw_retries=0
rk-pcie fe150000.pcie: failed to initialize host
```

This rollback is intentionally conservative. It does not prove hardware is good
or bad. It restores the RK3588 host to a state where the RK1828 runtime stack
cannot start automatically, so the next RK1828-first power test can separate
hardware/power-order behavior from RKNN3 software startup behavior.

## Current Conclusion

RK1828 is now online from the RK3588 host's PCIe enumeration point of view when
the RK1828 12V rail is powered before the RK3588 host boots.

Use this Bus-Id for RKLLM3/RKNN3 runtime commands:

```text
0000:01:00.0
```

Do not mark full model runtime as validated yet. The hardware is detected, the
patched RKEP driver lets `rknn3_transfer_proxy` open the PCIe endpoint, and the
minimal smoke reaches `find_devices ret=0 n_devices=1`. The current unvalidated
step is `rknn3_init`, which hangs before model loading. See the "RKNN3 1.0.4
RKEP ABI Patch", "Current Runtime Blocker", and "Firmware Download Risk"
sections above for the latest state.

## Unsafe Runtime Attempt

After the corrected power timing was found, the RK1828 was visible and the RKEP
module could create:

```text
/dev/pcie-rkep-0000:01:00.0
```

`rknn3_transfer_proxy devices` also listed the PCIe endpoint:

```text
0000:01:00.0        b98e6c51    PCIE
```

The next test was unsafe: `pcie_upgrade_tool -s 0000:01:00.0 uf
/lib/firmware/rknn3_rk1820.img` and `/bin/rknn3_model_test ...` were launched
while `rknn3_transfer_proxy` was already running. Both commands hung without
output, then RK3588 disappeared from the LAN and the board showed the red LED
state.

Do not repeat this pattern. RK1828 access must be serialized:

```text
stop proxy -> firmware download -> start proxy -> model test
```

Future runtime operations should use the guarded wrapper:

```bash
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py status
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py preflight
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py devices
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py pcie-list
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py smi
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py stop-runtime
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py load-driver
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py start-proxy
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py vision-smoke
```

Firmware download is intentionally not part of the normal sequence. It requires
physical recovery access and an explicit risk flag:

```bash
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py firmware --allow-firmware-risk
```

## 2026-07-03 05:21 Reachability Check

After the user reported that the RK3588 had been powered on again, only
read-only network checks were run. No RK1828 runtime, firmware, proxy, model, or
driver command was executed.

Observed state:

```text
ssh 192.168.1.52:22: Operation timed out / No route to host
Mac ARP for 192.168.1.52: incomplete
home server ip neigh for 192.168.1.52: FAILED
home server ping 192.168.1.52: 100% packet loss
150.158.146.192:6280: TCP open, but SSH closes during login
LAN nmap: 192.168.1.52 not present
SSH hosts discovered: 192.168.1.9, .26, .39, .42, .50, .53
orangepi/orangepi login on the discovered non-.39 SSH hosts: permission denied
```

Conclusion: at that time, the RK3588 host had not returned as a reachable LAN
host and had not obviously taken a different DHCP address. Continue to treat the
board as not remotely recoverable until `status` can connect and print host
state.

## 2026-07-03 11:06 Recovery Test

The RK3588 host later returned on the LAN:

```text
orangepi5plus
wlP2p33s0 UP 192.168.1.52/24
system boot 2026-07-03 10:17
```

The first safe checks were run through `scripts/rk1828_safe_runtime.py`.

Observed good state:

```text
lspci: 0000:01:00.0 Processing accelerators [1200]: Rockchip Device [1d87:182a]
PCIe link: 5.0 GT/s x1
runtime files present: rknn3_transfer_proxy, pcie_upgrade_tool, rknn3_model_test
firmware present: /lib/firmware/rknn3_rk1820.img
patched module present: /usr/lib/modules/pcie-rkep.ko
smoke files present:
  Qwen3-VL-4B-vision-rk1828-prune.rknn
  Qwen3-VL-4B-vision-rk1828-prune.weight
rknn3.service: not installed/inactive
```

The patched RKEP driver loaded and created the device node:

```text
pcie_rkep 36864 0
crw------- 1 root root 10, 120 /dev/pcie-rkep-0000:01:00.0
```

The transfer-layer checks succeeded:

```text
rknn3_transfer_proxy devices:
List of ntb devices attached
0000:01:00.0        b98e6c51    PCIE

pcie_upgrade_tool ld:
Program directory: /usr/bin/
List of connected rkep devices
Addr=0000:01:00.0 [1d87:182a]
```

Starting `rknn3_transfer_proxy` succeeded and launched a per-device proxy:

```text
DeviceManager: started proxy pid=... for device=0000:01:00.0
rknn3_transfer_proxy_b98e6c51 -s 0000:01:00.0
ctrl: listening on 127.0.0.1:18821
```

However, RKNN3 device management still failed:

```text
rknn-smi -v: Failed to initialize rknnsmi
rknn-smi info -l: Failed to initialize rknnsmi
rknn-smi info -t board -d 0: Failed to initialize rknnsmi
```

The original installer also deploys `rknn-mdns` and sets
`RKNN3_NETWORK_SOCKET_FILE=/tmp/rk-mdns.ini`. The current recovered RK3588
runtime did not have `rknn-mdns.service` or `/etc/profile.d/rknn3-env.sh`
installed. Manually starting `rknn-mdns` created the ini file but discovered no
devices:

```text
rknn-mdns -t /tmp/rk-mdns.ini -s 2
/tmp/rk-mdns.ini:
NETWORK_SOCKET_DEVICES=

/tmp/mdns_discovery.log:
no devices found
```

Running `rknn-smi` as root with `RKNN3_NETWORK_SOCKET_FILE=/tmp/rk-mdns.ini`
still returned `Failed to initialize rknnsmi`. Setting
`NETWORK_SOCKET_DEVICES` manually to `127.0.0.1:18821`, `127.0.0.1:18898`,
and `tcp://127.0.0.1:...` variants also returned rc 255. This makes the missing
profile variable insufficient as a sole explanation, although the wrapper now
exports `RKNN3_NETWORK_SOCKET_FILE=/tmp/rk-mdns.ini` for client-side smoke
commands to match the vendor startup environment.

The vision smoke command:

```text
/bin/rknn3_model_test Qwen3-VL-4B-vision-rk1828-prune.rknn \
  Qwen3-VL-4B-vision-rk1828-prune.weight none none 0x3 1
```

ran under the guarded wrapper and timed out after 180 seconds with no model
output. The RK3588 host remained reachable afterward, and `stop-runtime` cleaned
the proxy processes.

Current working hypothesis: PCIe enumeration, the patched RKEP function driver,
the device node, `rknn3_transfer_proxy devices`, and `pcie_upgrade_tool ld` are
now working. The remaining blocker is the RK1828 endpoint firmware/device state:
RKNN3 device management cannot initialize, and model initialization waits until
timeout. Do not retry model tests until the firmware/boot state is understood.
Do not run firmware download except with physical recovery available and the
explicit `--allow-firmware-risk` flag.

## Next Checks

1. Keep the known-good power sequence: RK1828 12V first, then boot or reboot the
   RK3588 host.
2. Install or boot a RK3588 host kernel/runtime package that provides
   `CONFIG_PCIE_FUNC_RKEP=y` or an equivalent Rockchip RKEP module.
3. Re-run:

```text
lspci -nn | grep -Ei '182a|1828|processing'
grep CONFIG_PCIE_FUNC_RKEP /boot/config-$(uname -r)
rknn3_transfer_proxy devices
```

4. Retry the vision smoke program against Bus-Id `0000:01:00.0`.
5. After C API init succeeds, copy the full
   `/home/wq/edge-model-lab/models/artifacts/rk1828/qwen3-vl-4b` bundle from the
   home server to the RK3588 host.
6. Start `rkllm3-server` with `--device-id 0000:01:00.0`.
7. Run a small request against the OpenAI-compatible chat endpoint and record
   output, memory, power, and temperature observations.
