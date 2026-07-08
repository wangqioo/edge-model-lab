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

Do not mark full model runtime as validated yet. The hardware is detected, and
the proxy can list the PCIe endpoint, but RKNN3 runtime startup is not validated.
The installer-provided service previously made the RK3588 host unreachable after
manual restart, and the runtime stack is currently isolated in the rollback
backup directory.

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
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py devices
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py stop-runtime
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py load-driver
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py firmware
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py start-proxy
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py vision-smoke
```

## Serialized Firmware Attempt

On 2026-07-03 evening, the guarded wrapper was used to repeat the bring-up
sequence without concurrent RK1828 runtime operations.

Successful checks before firmware download:

```text
RK3588 SSH reachable at 192.168.1.52
lspci: 0000:01:00.0 Processing accelerators [1200]: Rockchip [1d87:182a]
/usr/lib/modules/pcie-rkep.ko present
insmod pcie-rkep.ko succeeded
/dev/pcie-rkep-0000:01:00.0 created
rknn3.service inactive / no unit file
rknn3_transfer_proxy devices:
0000:01:00.0        b98e6c51    PCIE
```

The next step was run through the serialized wrapper:

```bash
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py stop-runtime
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py firmware
```

`firmware` launched:

```text
/bin/pcie_upgrade_tool -s 0000:01:00.0 uf /lib/firmware/rknn3_rk1820.img
```

No `rknn3_transfer_proxy`, model test, VLM demo, LLM demo, or `rkllm3-server`
process was running at the time. The firmware command produced no output, did
not return through the wrapper timeout, and RK3588 became unreachable from the
Mac:

```text
ping 192.168.1.52: 100% packet loss
ssh 192.168.1.52: Operation timed out
```

This narrows the blocker: the host failure is not only caused by concurrent
proxy/model access. The serialized firmware download path itself can wedge the
RK3588 host with the current RK1828 runtime package, firmware, RKEP module, or
power/runtime combination.

## Recovery After Serialized Firmware Hang

After physically recovering the hardware, the RK3588 host came back on LAN:

```text
ping 192.168.1.52: reachable
ssh: reachable
hostname: orangepi5plus
system boot: 2026-07-03 18:17
```

The first post-recovery command was the read-only wrapper status check. It
showed the desired safe baseline:

```text
lspci: 0000:01:00.0 Processing accelerators [1200]: Rockchip [1d87:182a]
/usr/lib/modules/pcie-rkep.ko present
/dev/pcie-rkep-* absent before driver load
rknn3.service inactive / no unit file
no RK1828 runtime processes
```

The staged driver and transfer-layer checks succeeded again:

```bash
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py load-driver
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py devices
```

Result:

```text
pcie_rkep loaded
/dev/pcie-rkep-0000:01:00.0 created
rknn3_transfer_proxy devices:
0000:01:00.0        b98e6c51    PCIE
```

This confirms the board can recover to the PCIe/RKEP/transfer-discovery layer
after removing the bad runtime state. The remaining blocker is specifically at
or before firmware download through `pcie_upgrade_tool ... uf`, not initial
PCIe enumeration, RKEP module loading, or transfer device discovery.

## 2026-07-07 rknn-smi Init Failure

Observed symptom:

```text
root@orangepi5plus:~# rknn-smi info
Failed to initialize rknnsmi
```

Initial read-only status showed:

```text
lspci: 0000:01:00.0 Processing accelerators [1200]: Rockchip [1d87:182a]
/usr/lib/modules/pcie-rkep.ko: missing
/dev/pcie-rkep-*: missing
rknn3.service: active/enabled
rknn3_transfer_proxy: running
```

The service log explained the first failure:

```text
rknn3_startup: warning: failed to get pcie-rkep.ko
rknn3_startup: Failed to load driver or find device
```

The module had been left in backup/isolation locations:

```text
/usr/lib/modules/pcie-rkep.ko.bak-20260703045926
/home/orangepi/rk1828-rknn3-runtime-disabled-20260703-034331/usr/lib/modules/pcie-rkep.ko
```

After restoring `/usr/lib/modules/pcie-rkep.ko` and running only the guarded
driver step:

```bash
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py load-driver
```

the driver and device node came up:

```text
pcie_rkep              36864  0
/dev/pcie-rkep-0000:01:00.0
```

The transfer layer also listed the RK1828:

```text
rknn3_transfer_proxy devices:
0000:01:00.0        b98e6c51    PCIE
```

`rknn-smi info` still failed after that. Additional checks showed
`pcie_upgrade_tool ld` can see the endpoint, while `/tmp/rk-mdns.ini` was absent
or contained no socket devices:

```text
Addr=0000:01:00.0 [1d87:182a]
NETWORK_SOCKET_DEVICES=
Failed to initialize rknnsmi
```

The vendor suggested adding delays in `/bin/rknn3_startup`: `sleep 2` after
driver load and `sleep 10` after firmware update. That patch was installed on
the RK3588 host with backup:

```text
/bin/rknn3_startup.bak-20260707195117
```

The same delay windows were also added to `scripts/rk1828_safe_runtime.py` so
future guarded runs do not depend on the board-local startup script.

High-risk boundary: the patched `/bin/rknn3_startup start` was not executed in
this session, because it proceeds into `pcie_upgrade_tool ... uf` firmware
download. Earlier serialized firmware download attempts on this runtime stack
made the RK3588 host unreachable. Retry that path only with local recovery or
serial console available.

## 2026-07-07 RKEP Driver Version Fix

`rknn-smi` debug logging exposed the concrete reason initialization failed:

```text
pcie_rkep drv version 0x0 is not compatible, at least 0x30301
rknnsmi init pcie failed, ret=-6
```

The installed `pcie-rkep.ko` could enumerate PCIe and create
`/dev/pcie-rkep-0000:01:00.0`, but it did not return the function driver
version expected by the RKNN3 `1.0.4` / `rknn-smi 1.3.0` user-space stack.

The matching Orange Pi `6.1.43-rockchip-rk3588` kernel tree on the home server
already had the RKEP version ioctl wired:

```text
/home/wq/edge-tools/orangepi-kernel/linux-orangepi-6.1.43-full
include/uapi/linux/rk-pcie-ep.h: RKEP_FUNC_DRV_VERSION
drivers/misc/rockchip/pcie-rkep.c: PCIE_EP_GET_FUNC_DRV_VERSION
```

`RKEP_FUNC_DRV_VERSION` was updated from `0x30300` to the user-space-required
`0x30301`, then `pcie-rkep.ko` was rebuilt:

```text
sha256: 2343ebd6bf3826e3f1da747b3101826522ade509112725b26a4559f2dd9d16df
vermagic: 6.1.43-rockchip-rk3588 SMP mod_unload aarch64
alias: pci:v00001D87d0000182Asv*sd*bc*sc*i*
```

The new module was installed to:

```text
/usr/lib/modules/pcie-rkep.ko
/lib/modules/pcie-rkep.ko
```

After unloading the old module and loading the rebuilt one, `rknn-smi` no longer
failed during initialization:

```text
rknn-smi info -l
  Device Count                  : 1
    Device ID                   : 0
    Communication mode          : PCIe
    Chip Count                  : 0

rknn-smi info
| 0             Offline  | NA | NA | NA |
```

This is a real layer of progress: the host RKEP version handshake now passes,
and RKNN3 user space can see the RK1828 as a PCIe SMI device. The device remains
offline because the RK1828 firmware/application side is not alive yet.

## 2026-07-07 Firmware Attempt After RKEP Version Fix

After the RKEP version fix, the guarded sequence was retried:

```bash
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py start-proxy
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py firmware
```

`start-proxy` succeeded and listed:

```text
0000:01:00.0        b98e6c51    PCIE
```

`firmware` then entered:

```text
/bin/pcie_upgrade_tool -s 0000:01:00.0 uf /lib/firmware/rknn3_rk1820.img
```

The command did not return, and the RK3588 host stopped responding on LAN:

```text
ping 192.168.1.52: 100% packet loss
ssh 192.168.1.52: no response
```

This confirms the remaining blocker is not the RKEP driver version check. It is
at or below firmware download / RK1828 boot handoff. Do not retry firmware
download remotely without local recovery or serial console. The next variable
must be one of:

- a vendor-confirmed RK1828 M.2 firmware/runtime package matching this board,
- a stronger/measured 12V supply and thermal check,
- serial console or local display observation during `pcie_upgrade_tool ... uf`,
- a vendor-provided `pcie-rkep.ko`/firmware pair known to work together.

## 2026-07-08 Recovery And Read-Only State

After physical recovery, the RK3588 host came back on LAN:

```text
2026-07-08 00:44 CST
ping 192.168.1.52: reachable
hostname: orangepi5plus
kernel: 6.1.43-rockchip-rk3588
uptime: about 1 minute
```

The first command was the read-only report:

```bash
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py post-recovery-report
```

It confirmed the safe baseline:

```text
lspci: 0000:01:00.0 Processing accelerators [1200]: Rockchip [1d87:182a]
rknn3.service: inactive, disabled
rknn-mdns.service: inactive, disabled
no RK1828 runtime processes
```

However, the recovery had restored or left the old RKEP module in the live paths:

```text
d60794519a45e582d12e02ccfcd741acb374bcb82924678149c49fc1089ef656  /usr/lib/modules/pcie-rkep.ko
d60794519a45e582d12e02ccfcd741acb374bcb82924678149c49fc1089ef656  /lib/modules/pcie-rkep.ko
ls: cannot access '/dev/pcie-rkep-*': No such file or directory
```

The fixed module was copied back from the Mac and installed to both live paths:

```text
2343ebd6bf3826e3f1da747b3101826522ade509112725b26a4559f2dd9d16df  /usr/lib/modules/pcie-rkep.ko
2343ebd6bf3826e3f1da747b3101826522ade509112725b26a4559f2dd9d16df  /lib/modules/pcie-rkep.ko
```

After `insmod`, the host driver and device node were healthy:

```text
pcie_rkep              36864  0
crw------- 1 root root 10, 120 /dev/pcie-rkep-0000:01:00.0
Kernel driver in use: pcie-rkep
```

Read-only SMI and transfer checks then reached the same layer as before:

```text
rknn-smi info -l:
  Device Count                  : 1
    Device ID                   : 0
    Communication mode          : PCIe
    Product Name                : NA
    Serial Number               : NA
    Chip Count                  : 0

rknn-smi info:
| 0             Offline  | NA | NA | NA |

pcie_upgrade_tool ld:
Addr=0000:01:00.0 [1d87:182a]

rknn3_transfer_proxy devices:
0000:01:00.0        b98e6c51    PCIE
```

Important debug lines from `/var/log/rknn-smi.log`:

```text
rk pcie tiny version: 30301
open rkep: /dev/pcie-rkep-0000:01:00.0 Success.
rc_cc_version=30301
ep_cc_version=7bfdc9db
hw_reset, 18, 13
PCIe device 0 is not alive
rknnsmi init success
```

`rknn-smi -v` still reports no live connect versions:

```text
rknn-smi version              : 1.3.0
PCIe driver version           : NA
RC chips connect version      : NA
EP chips connect version      : NA
rknn3 API version             : 1.0.4
```

This narrows the current boundary. The RK3588 host side is now correct through
PCIe enumeration, RKEP module binding, RKEP version `0x30301`, and transfer
device discovery. The failing layer is RK1828 endpoint liveness after boot or
firmware handoff.

The installed firmware image matches the cached RKNN3 SDK `1.0.4` M.2 installer:

```text
83807abd6e068e52fdd27436d9e06a9db9d9e69d285b1c1379fa16ab3fe1e884  /lib/firmware/rknn3_rk1820.img
83807abd6e068e52fdd27436d9e06a9db9d9e69d285b1c1379fa16ab3fe1e884  .cache/rk1828-release-v1.0.4/installer/system_root/lib/firmware/rknn3_rk1820.img
```

The official RKNN3 Quick Start only documents checking RK1820/RK1828 connection
with:

```text
./rknn3_transfer_proxy devices
```

and the expected PCIe device row. This board already passes that documented
connection check. The remaining `Offline` state needs vendor guidance for
firmware download / loader / endpoint liveness, not another model conversion or
another `rknn3_transfer_proxy devices` check.

## Local Reference Recheck

After the 2026-07-08 recovery, the older RK182X `V1.0.0` documents, the
RM182XMC0 hardware design guide, and the M.2-to-PCIe carrier guide were checked
again because the RKNN3 `V1.0.4` Quick Start stops at
`rknn3_transfer_proxy devices` for the connection check.

Relevant local files:

```text
/Users/wq/Downloads/开发资料/05_RKNN3软件SDK_V1.0.0/01_ReleaseNote与QuickStart_V1.0.0/01_Rockchip_RK182X_Quick_Start_RKNN3_SDK_V1.0.0_CN.pdf
/Users/wq/Downloads/开发资料/02_底板与参考设计/01_M2转PCIe扩展板/02_使用说明/RK1820_M2_TO_PCIE_Guide_V1.1_20260312_CN.pdf
/Users/wq/Downloads/开发资料/01_硬件核心资料/02_硬件设计指南/Rockchip RM182XMC0 Hardware_Design_Guide_V1.1_CN_20260415.pdf
```

Findings:

- The RKNN3 `V1.0.0` and `V1.0.4` Quick Starts both use
  `rknn3_transfer_proxy devices` as the documented RK1820/RK1828 connection
  check. This board passes that check.
- The M.2-to-PCIe guide says the carrier needs independent 12V power and
  recommends `12V/3A` or above.
- The same M.2-to-PCIe guide lists the kit adapter as `12V/5A`.
- The RM182XMC0 hardware design guide says the module needs additional
  `12V/3A` power from the baseboard.
- The hardware design guide documents `SARADC_IN0_BOOT` floating as default
  `PCIe2.1 BOOT`, and pulled down with `0R` as optional `USB2.0 BOOT`.
- The hardware design guide says `PIN50` is reset input, active low, controlled
  by the host GPIO.

This changes the priority of the next experiment. A `12V/1A` supply may be
enough for LED/fan/PCIe enumeration, but it is below the documented current
requirement and is not a valid basis for firmware download or endpoint liveness
testing. Before another `pcie_upgrade_tool ... uf` attempt, use a measured
`12V/3A+` supply, preferably the documented `12V/5A` class supply, and observe
the board locally.

The Mac-side wrapper was then tightened so this dangerous action cannot be
rerun accidentally:

```text
scripts/rk1828_safe_runtime.py firmware
```

now exits locally before SSH unless the caller explicitly passes:

```text
--allow-firmware-hang
```

A new read-only action was added for the first check after physical recovery:

```bash
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py post-recovery-report
```

That report collects PCIe state, module metadata, userspace and firmware hashes,
service state, `rknn-smi info -l`, `rknn-smi info`, `/var/log/rknn-smi.log`, and
recent kernel logs. It does not run `insmod` or `pcie_upgrade_tool ... uf`.

## 2026-07-08 Orange Pi Host Adaptation Without Reflashing

After the RK3588 host was physically rebooted, LAN access recovered:

```text
ping 192.168.1.52: 3/3 received
```

The first read-only recovery report showed a useful but incomplete state:

```text
lspci: 0000:01:00.0 Processing accelerators [1200]: Rockchip [1d87:182a]
/usr/lib/modules/pcie-rkep.ko sha256:
2343ebd6bf3826e3f1da747b3101826522ade509112725b26a4559f2dd9d16df
/dev/pcie-rkep-*: absent
rknn-smi: Failed to initialize rknnsmi
```

This confirmed that the fixed RKEP module survived the reboot, but it was not
autoloaded. Manually running the guarded `load-driver` action restored the host
PCIe/RKEP layer:

```text
pcie_rkep              36864  0
crw------- 1 root root 10, 120 /dev/pcie-rkep-0000:01:00.0
```

The Orange Pi host was then adapted without reflashing by installing a dedicated
oneshot service:

```text
/etc/systemd/system/rk1828-rkep-load.service
/usr/local/sbin/rk1828-rkep-load
```

The service only runs PCI rescan, loads `/usr/lib/modules/pcie-rkep.ko`, waits
for the device node, and exits. It does not start `rknn3_transfer_proxy`, does
not start RKNN3 services, and does not run `pcie_upgrade_tool ... uf`.

Verified service state:

```text
systemctl is-enabled rk1828-rkep-load.service: enabled
systemctl is-active rk1828-rkep-load.service: active
```

After this adaptation, the host layer is repeatable:

```text
lspci: 0000:01:00.0 [1d87:182a]
pcie_rkep loaded
/dev/pcie-rkep-0000:01:00.0 exists
rknn-smi info -l:
  Device Count: 1
  Communication mode: PCIe
  Chip Count: 0
rknn-smi info:
  Device 0 Offline
```

The remaining failure is unchanged and now isolated below host enumeration,
driver load, and SMI initialization:

```text
rk pcie tiny version: 30301
rc_cc_version=30301
ep_cc_version=7bedc9fb
hw_reset, 18, 13
PCIe device 0 is not alive
```

The EVB10 `boot.img` was inspected as a FIT image, and its embedded FDT was
extracted from offset `0x800` with size `0x4a963`. Comparing the EVB10 FDT with
the live Orange Pi DTB showed that `pcie@fe150000` has the same essential host
controller shape: Gen3, four lanes, same ranges, same DBI/config addresses, and
status `okay`. The `reset-gpios` and regulator phandles differ, but those are
board-specific wiring details and cannot be copied directly from EVB10 to
Orange Pi.

Current conclusion: reflashing is not required to make the Orange Pi host reach
a stable PCIe/RKEP/SMI discovery state. The unresolved blocker is RK1828
endpoint liveness after reset or firmware handoff, not host-side module loading.
Further work needs either serial/kernel logs during `pcie_upgrade_tool ... uf`,
a vendor-confirmed RK1828 firmware/update image, or exact guidance for the
meaning of `hw_reset, 18, 13`.

## 2026-07-08 PCIe MaskROM And Direct Firmware Attempt

Further probing found a more precise endpoint state. Running `pcie_upgrade_tool`
as root with the non-writing test command succeeded:

```text
/bin/pcie_upgrade_tool -s 0000:01:00.0 td
Testing device...
Soc=rk1820 Addr=0000:01:00.0 Mode=MaskROM [1d87:182a]
Testing device OK
```

This means the RK1828 endpoint is reachable over PCIe and is currently in
MaskROM mode. The previous `Offline` result is therefore not a generic PCIe
enumeration failure; the endpoint is waiting for a bootloader/firmware flow.

The firmware image was inspected locally:

```text
sha256: 83807abd6e068e52fdd27436d9e06a9db9d9e69d285b1c1379fa16ab3fe1e884
header: RKFW
contains: LDR, RKNS, loader, parameter, rootfs, rk1820
does not contain string: rk1828
```

The lack of an `rk1828` string is not proof that the image is wrong, because the
package may use RK1820 naming for the RK182X family, but it is now an explicit
vendor-confirmation item.

A new guarded Mac-side action was added:

```bash
EDGE_ORANGE_RK3588_PASSWORD=orangepi \
  ./scripts/rk1828_safe_runtime.py firmware-direct --allow-firmware-hang
```

It differs from the earlier firmware attempt in three ways:

```text
1. refuses to run if rknn3_transfer_proxy is active,
2. runs `pcie_upgrade_tool ... td` first to confirm MaskROM reachability,
3. passes an explicit temporary directory: `uf "$firmware_path" /tmp/rk1828-fw`.
```

The direct attempt reproduced the failure faster:

```text
=== direct firmware download without proxy ===
Testing device...
Soc=rk1820 Addr=0000:01:00.0 Mode=MaskROM [1d87:182a]
Testing device OK
```

Immediately after `uf` started, the RK3588 host stopped responding to ping:

```text
ping 02:31:06 ok
ping 02:31:07 ok
ping 02:31:08 fail
...
```

Local hanging SSH/wrapper processes were killed. The board again needs physical
recovery.

This rules out `rknn3_transfer_proxy` interference as the primary cause of the
host drop. The failure is now isolated to the `pcie_upgrade_tool uf` transition
from MaskROM to loader/firmware. The next useful variables are:

```text
1. a vendor-confirmed RK1828/RK182X firmware image or update.img,
2. a vendor-confirmed sequence such as db bootloader -> uf firmware -> run,
3. kernel/serial logs during the first seconds of `uf`,
4. an official RK3588 EVB10 host run for A/B comparison.
```

### 2026-07-08 Post-Reboot Narrowing

After physical reboot, the custom driver autoload service survived and did what
it was meant to do:

```text
systemctl is-active rk1828-rkep-load.service -> active
/dev/pcie-rkep-0000:01:00.0 exists
pcie_upgrade_tool ld -> Addr=0000:01:00.0 [1d87:182a]
```

The read-only PCIe boot test also remained stable:

```text
pcie_upgrade_tool -s 0000:01:00.0 td
Soc=rk1820 Addr=0000:01:00.0 Mode=MaskROM [1d87:182a]
Testing device OK
```

The official SDK quick-start connectivity check now passes on this adapted
Orange Pi host:

```text
rknn3_transfer_proxy devices
List of ntb devices attached
0000:01:00.0        b98e6c51    PCIE
```

That means the host can enumerate the PCIe endpoint and the RKNN3 transfer tool
can see the coprocessor transport. The failure is not basic PCIe detection.

Additional `pcie_upgrade_tool` subcommands narrow the state machine:

```text
rvd <id> -> Device is not in loader mode
rd       -> Device is not in loader mode
```

Neither command dropped the RK3588 host. This suggests `rvd` and `rd` require
the RK182X endpoint to have already moved from MaskROM into loader mode, and the
host drop is specific to the `uf` loader/firmware download transition rather
than every `pcie_upgrade_tool` operation.

The RKNN3 firmware image was unpacked locally with `afptool-rs` to inspect its
Rockchip RKFW/RKAF structure without touching the board:

```text
rknn3_rk1820.img
  RKFW BOOT: 92551 bytes
  embedded RKAF update: 3278852 bytes
  manufacturer: RK1820
  model: RK1820
  partitions:
    parameter.mem
    subsoc_rtt.img
    node2_rtt.img
    node4_rtt.img
    rk1820_ddr_v1.15.bin
```

String inspection of the runtime images also reports `RK1820` in
`subsoc_rtt.img`, `node2_rtt.img`, and `node4_rtt.img`. This is not enough by
itself to prove the package is wrong for RK1828K, because Rockchip may package
RK182X firmware under RK1820 naming. It is, however, now a concrete
vendor-confirmation item: this exact image must be confirmed as valid for
RK1828K, or replaced with a dedicated RK1828/RK1828K image.

USB fallback was checked from the RK3588 host. `lsusb` did not show the
Rockchip USB update-mode ID used by the installer script:

```text
USB update ID expected by rknn_upgrade_tool: 2207:180b
observed: no 2207:180b device
```

So the current wiring exposes RK1828K over PCIe only; the installer wrapper's
USB `upgrade_tool ufx` path is not available unless the module's USB update
interface is physically exposed.

### 2026-07-08 Bootloader-Only Isolation

The RKFW `BOOT` payload was extracted locally from `rknn3_rk1820.img`:

```text
tmp/rk1828-fw-unpack/rkfw/BOOT
size: 92551 bytes
sha256: 6dac3fec660fa5720c81a0850b793ca5be1e010e0574df3c428e8465268e4bea
```

It was copied to the RK3588 host as `/tmp/rk1828-fw/BOOT`, and a guarded
bootloader-only action was used:

```bash
./scripts/rk1828_safe_runtime.py bootloader-direct \
  --allow-bootloader-download \
  --bootloader-path /tmp/rk1828-fw/BOOT
```

Result:

```text
Testing device...
Soc=rk1820 Addr=0000:01:00.0 Mode=MaskROM [1d87:182a]
Testing device OK
Downloading bootloader...
Downloading bootloader OK
Testing device...
Soc=rk1820 Addr=0000:01:00.0 Mode=Loader [1d87:182a]
Testing device OK
```

The RK3588 host stayed pingable during this bootloader-only transition. This is
the first confirmed path from MaskROM to Loader on the Orange Pi host.

After that, the official `rknn3_transfer_proxy devices` still listed the PCIe
device, and `pcie_upgrade_tool td` confirmed `Mode=Loader`. `rknn-smi info -l`
still reported the PCIe device as not alive, which is expected if only loader is
running and the full RKNN3 runtime firmware has not been downloaded.

However, attempting Loader-state interaction with `rvd <id>` hung and the
RK3588 host then became unreachable. This narrows the failure further:

```text
Safe:
  MaskROM td
  transfer_proxy devices
  db extracted BOOT -> Loader

Unsafe observed:
  uf full firmware image
  Loader-state rvd / SMI-style interaction after db
```

The remaining risky transition is therefore not bootloader download itself. It
is the handoff after Loader starts: either full firmware/DDR/RTT download, the
Loader command protocol, or PCIe DMA/message setup once the Loader is active.

After the next physical reboot, the host returned to the clean baseline again:

```text
rk1828-rkep-load.service: active
/dev/pcie-rkep-0000:01:00.0 exists
pcie_upgrade_tool ld -> Addr=0000:01:00.0 [1d87:182a]
pcie_upgrade_tool td -> Mode=MaskROM
rknn3_transfer_proxy devices -> 0000:01:00.0 b98e6c51 PCIE
```

No `pcie_upgrade_tool`, `rknn-smi`, or RKNN3 runtime processes were left
running. `/sys/fs/pstore` was empty after recovery, and the previous boot's
journal did not include a panic/oops trace around the host drop. The failure
therefore did not leave a captured Linux panic record; it behaves more like a
hard PCIe/kernel hang or board-level reset/power event.

Because Loader-state `rvd` was shown to be unsafe on this host, the local
wrapper now refuses `read-vendor` unless `--allow-loader-interaction` is passed
explicitly.

### 2026-07-08 Vendor Delay Retest

The seller suggested adding delays to `rknn3_startup`. The RK3588 host already
had those changes in both `/bin/rknn3_startup` and `/usr/bin/rknn3_startup`:

```sh
# wait after driver load
sleep 2

# wait after firmware update
sleep 10
```

Before the retest, the safe baseline was:

```text
lspci -> 0000:01:00.0 [1d87:182a]
/dev/pcie-rkep-0000:01:00.0 exists
pcie_upgrade_tool td -> Soc=rk1820 Addr=0000:01:00.0 Mode=MaskROM [1d87:182a], Testing device OK
rknn3_transfer_proxy devices -> 0000:01:00.0 b98e6c51 PCIE
rknn-smi info -> Device Count 1, PCIe, Offline, Chip Count 0
```

`rknn-smi` debug output now proves that SMI can open the RKEP device, but the
endpoint application is not alive:

```text
open rkep: /dev/pcie-rkep-0000:01:00.0 Success.
id=182a1d87
magic=18, ver=49f76a3c
ep_cc_version=5bedd9db
gen2x1
hw_reset, 18, 17
PCIe device 0 is not alive
Total EP device num: 1
rknnsmi init success
```

Then the delayed startup script was run manually:

```bash
/bin/rknn3_startup stop
/bin/rknn3_startup start
```

It still made the RK3588 host unreachable:

```text
start:open rknn3_transfer_proxy
find device 0000:01:00.0
Timeout, server 192.168.1.52 not responding.
SSH_STARTUP_COMMAND_FAILED=255
```

Immediate ping and SSH checks failed:

```text
6 packets transmitted, 0 packets received, 100.0% packet loss
ssh: connect to host 192.168.1.52 port 22: Host is down
```

The local log is:

```text
tmp/rk1828-vendor-startup-20260708-093211.log
```

This proves the seller's delay-only workaround is insufficient on this hardware
and runtime stack. The failure still occurs during or immediately after the
startup script launches firmware download for `0000:01:00.0`.

A standalone escalation report for the seller was written to:

```text
docs/experiments/2026-07-08-rk1828k-vendor-escalation.md
```

### 2026-07-08 Loader To Firmware Retest

After another reboot, `/tmp/rk1828-fw/BOOT` was gone because it lived under
`/tmp`, so the extracted BOOT payload was copied to the RK3588 host again:

```text
sha256(/tmp/rk1828-fw/BOOT)=6dac3fec660fa5720c81a0850b793ca5be1e010e0574df3c428e8465268e4bea
```

Bootloader download was repeatable and did not drop the host:

```text
pcie_upgrade_tool -s 0000:01:00.0 td
Soc=rk1820 Addr=0000:01:00.0 Mode=MaskROM [1d87:182a]
Testing device OK

pcie_upgrade_tool -s 0000:01:00.0 db /tmp/rk1828-fw/BOOT
Downloading bootloader OK

pcie_upgrade_tool -s 0000:01:00.0 td
Soc=rk1820 Addr=0000:01:00.0 Mode=Loader [1d87:182a]
Testing device OK
```

Then `rd` from Loader mode returned success, but the device remained in Loader:

```text
pcie_upgrade_tool -s 0000:01:00.0 rd
Device reset OK

pcie_upgrade_tool -s 0000:01:00.0 td
Soc=rk1820 Addr=0000:01:00.0 Mode=Loader [1d87:182a]
Testing device OK
```

Finally, full firmware download was attempted from the confirmed Loader state,
without `rknn3_transfer_proxy`, and with an explicit tmp directory:

```bash
pcie_upgrade_tool -s 0000:01:00.0 uf /lib/firmware/rknn3_rk1820.img /tmp/rk1828-fw
```

It still made the RK3588 host unreachable:

```text
Timeout, server 192.168.1.52 not responding.
UF_SSH_FAILED=255

8 packets transmitted, 0 packets received, 100.0% packet loss
ssh: connect to host 192.168.1.52 port 22: Operation timed out
```

The local log is:

```text
tmp/rk1828-loader-uf-direct-20260708-094412.log
```

This removes the simple explanation that the official startup script fails only
because it skipped an explicit bootloader step. The explicit `db BOOT` step is
safe and reaches Loader; `uf rknn3_rk1820.img` still fails from Loader. The
remaining suspect area is the full firmware image contents, the DDR/RTT handoff,
or RK1828K-specific PCIe/Loader protocol compatibility.

## Next Checks

1. Keep `rk1828-rkep-load.service` enabled so rebooted hosts automatically
   expose `/dev/pcie-rkep-0000:01:00.0`.
2. Do not retry `pcie_upgrade_tool ... uf` on this exact runtime stack without a
   new variable to test, such as a vendor-confirmed RK3588 host runtime package,
   a different RK1828 firmware image, a measured stronger 12V supply, or direct
   local serial/console observation.
3. After each recovery or reboot, first run the read-only report:

```bash
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py post-recovery-report
```

4. Then re-run only read-only and driver checks:

```text
./scripts/rk1828_safe_runtime.py test-device
./scripts/rk1828_safe_runtime.py devices
lspci -nn | grep -Ei '182a|1828|processing'
grep CONFIG_PCIE_FUNC_RKEP /boot/config-$(uname -r)
lsmod | grep pcie_rkep
ls -l /dev/pcie-rkep-*
```

5. Ask the vendor to confirm the exact firmware/update package and sequence for
   RK1828K:

```text
供电已修正，Host 侧 PCIe/RKEP/SMI 稳定。
pcie_upgrade_tool -s 0000:01:00.0 td 返回：
Soc=rk1820 Addr=0000:01:00.0 Mode=MaskROM [1d87:182a], Testing device OK。
rknn3_transfer_proxy devices 返回：
0000:01:00.0 b98e6c51 PCIE。
但无 proxy、显式 tmp_dir 执行：
pcie_upgrade_tool -s 0000:01:00.0 uf /lib/firmware/rknn3_rk1820.img /tmp/rk1828-fw
1-2 秒后 RK3588 整机掉线。
单独拆出 BOOT 后执行：
pcie_upgrade_tool -s 0000:01:00.0 db /tmp/rk1828-fw/BOOT
可以成功进入 Loader：
Soc=rk1820 Addr=0000:01:00.0 Mode=Loader [1d87:182a]。
但 Loader 后继续执行 rvd/SMI 交互会卡住并导致 RK3588 不可达。
本地拆包显示该 img 的 RKAF manufacturer/model 为 RK1820，包含 rk1820_ddr_v1.15.bin。
请确认：这个 img 是否适配 RK1828K？是否需要 RK1828K 专用 update.img/loader.bin？
是否应先执行 db loader.bin，再 uf/run？`hw_reset,18,13` 和 obj_info magic=18,ver=49f76e1c 分别表示什么？
```

6. Do not enter Loader and then run `rvd`, `rknn-smi`, or model runtime again
   without a new variable and local serial observation. The host became
   unreachable after that exact state.
7. If and only if a new runtime/firmware variable is introduced, repeat the
   staged sequence under local console observation:
   `stop-runtime -> load-driver -> firmware`.
8. Only after firmware download returns successfully and the host remains
   reachable should proxy and model runtime be retried:
   `start-proxy -> devices -> vision-smoke`.
9. After C API init succeeds, copy the full
   `/home/wq/edge-model-lab/models/artifacts/rk1828/qwen3-vl-4b` bundle from the
   home server to the RK3588 host.
10. Start `rkllm3-server` with `--device-id 0000:01:00.0`.
11. Run a small request against the OpenAI-compatible chat endpoint and record
   output, memory, power, and temperature observations.
