# RK1828 Qwen3-VL-4B Runbook

This runbook is for the RK1828 M.2 accelerator attached to the RK3588 host.

## Network Topology

The Mac control machine, RK3588 host, and home server are on the same LAN. Use
LAN SSH for RK1828 bring-up, module builds, and large file transfers whenever
available:

```text
Mac control machine: 192.168.1.26
RK3588 host:         orangepi@192.168.1.52:22
Home server:         wq@192.168.1.39:22
```

The FRP/public endpoints in `devices.yaml` are fallback paths. On the Mac,
`devices.local.yaml` overrides `orange-rk3588` to the LAN address so
`./scripts/edgectl ... orange-rk3588` uses `192.168.1.52`.

## Current State

`Qwen/Qwen3-VL-4B-Instruct` has been converted for RK1828 with RKNN3 Toolkit `1.0.4`.

Converted artifacts are already on the home server:

```text
/home/wq/edge-model-lab/models/artifacts/rk1828/qwen3-vl-4b
```

Runtime validation has moved past the initial RK3588 host-kernel transfer
blocker. With the correct power sequence, the RK1828 is visible in PCIe as
`0000:01:00.0`. A rebuilt Orange Pi `6.1.43-rockchip-rk3588` RKEP module can
load and create `/dev/pcie-rkep-0000:01:00.0`.

On 2026-07-03, a second RKEP compatibility issue was found and patched locally:
RKNN3 `1.0.4` user space requires RKEP function-driver version `0x30300` via
`_IOR('P', 0, int)` and mmap resources for BAR1/BAR5 at indexes 7 and 8. The
original Orange Pi 6.1.43 driver returned version `0x0` and rejected mmap index
7/8. After patching and rebuilding the module, `rknn3_transfer_proxy` opened the
device and logged:

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

This is not yet full model success. A minimal RKNN3 smoke reached
`find_devices ret=0 n_devices=1`, then hung inside `rknn3_init`. A
`pcie_upgrade_tool ... uf /lib/firmware/rknn3_rk1820.img` attempt after stopping
proxy/model processes made the RK3588 host unreachable on LAN. Do not repeat
firmware download unless physical power recovery is available.

Earlier in the bring-up, the RKNN3 M.2 runtime and custom RKEP module were
isolated out of the live RK3588 system paths for recovery:

```text
/home/orangepi/rk1828-rknn3-runtime-disabled-20260703-034331
```

After this isolation rollback, the RK3588 host rebooted normally without RK1828
power. The later 2026-07-03 RK1828-first boot test restored the RKNN3 user-space
runtime and installed the patched RKEP module manually, without enabling
`rknn3.service`. The last confirmed reachable runtime state had the patched
`/usr/lib/modules/pcie-rkep.ko` installed and `rknn3_transfer_proxy` able to open
the RK1828 PCIe device. The host then became unreachable during a manual
firmware download attempt.

## What Is Ready

The server-side conversion environment is ready:

```text
/home/wq/edge-tools/rknn3-qwen3vl-py310
/home/wq/lincaigui/rknn3-model-zoo
/home/wq/edge-model-sources/huggingface/Qwen/Qwen3-VL-4B-Instruct
```

The runtime bundle contains:

```text
vision/Qwen3-VL-4B-vision-rk1828-prune.rknn
vision/Qwen3-VL-4B-vision-rk1828-prune.weight
llm/Qwen3-VL-4B-llm-rk1828.rknn
llm/Qwen3-VL-4B-llm-rk1828.weight
llm/Qwen3-VL-4B-llm.config.pkl
llm/Qwen3-VL-4B-llm.tokenizer.gguf
llm/Qwen3-VL-4B-llm.embed.bin
```

The tracked metadata lives in:

```text
models/assets.yaml
models/artifacts/rk1828/qwen3-vl-4b/README.md
models/artifacts/rk1828/qwen3-vl-4b/manifest.yaml
docs/experiments/2026-07-02-rk1828-qwen3-vl-4b-rknn3-conversion.md
```

## Power Assumption

The RK1828 card should not be expected to work from the RK3588 M.2 slot alone. Use separate 12V power before runtime checks.

If the 12V supply is limited to 12V 1A, treat it as a cautious bring-up supply only until measured. It may be enough for idle or detection, but full Qwen3-VL runtime can exceed that depending on RK1828 load, fan, and carrier-board losses.

## Required Power Sequence

Power sequencing matters for PCIe enumeration and for RK3588 boot stability.

Known-good sequence from the 2026-07-03 bring-up:

1. Connect and enable RK1828 separate 12V power first.
2. Wait for the RK1828 board to finish its own startup, not only for the 12V LED
   to turn on. Treat a stable LED/fan state as the minimum observable signal.
3. Boot or reboot the RK3588 host only after RK1828 startup is stable.
4. Verify that `lspci -nn` shows the RK1828 endpoint.

Expected endpoint:

```text
0000:01:00.0 Processing accelerators [1200]: Rockchip Electronics Co., Ltd Device [1d87:182a]
```

If RK3588 boots before RK1828 12V is present, or while RK1828 is still in its own
startup transition, the M.2 PCIe controller can fail link training and RK1828
will not appear until the host is rebooted with RK1828 already fully started. In
that failed case, kernel logs showed:

```text
rk-pcie fe150000.pcie: PCIe Link Fail, LTSSM is 0x0
rk-pcie fe150000.pcie: failed to initialize host
```

Observed failure mode: powering RK3588 too soon after RK1828 12V can make the
RK3588 host appear stuck or temporarily unreachable. The corrected sequence is
therefore "RK1828 12V on, wait until RK1828 is fully up, then RK3588 power on",
not merely "RK1828 12V before RK3588".

## Host Kernel Requirement

RKNN3 coprocessor mode runs the application on RK3588 and controls the RK1828
through `rknn3_transfer_proxy`. The Rockchip RKNN3 SDK documents this mode as:

```text
RK3588 -> PCIe/USB/Ethernet -> RK1820/RK1828
```

For the current M.2 PCIe path, plain PCIe enumeration is not enough. The host
kernel must expose the Rockchip RKEP transfer path used by
`rknn3_transfer_proxy`.

Check the RK3588 host kernel:

```bash
uname -a
grep -E 'CONFIG_PCIE_FUNC_RKEP|CONFIG_NTB|CONFIG_UIO|CONFIG_VFIO' /boot/config-$(uname -r)
```

Current Orange Pi kernel result:

```text
Linux orangepi5plus 6.1.43-rockchip-rk3588 #1.0.8
# CONFIG_PCIE_FUNC_RKEP is not set
# CONFIG_NTB is not set
# CONFIG_UIO is not set
# CONFIG_VFIO is not set
```

Known failure signature with that kernel:

```text
E NPUTransfer: rk_pcie_device_init failed, bus: 0000:01:00.0!
E NPUTransfer: Transfer interface open failed!, PCIE: 0000:01:00.0, name = Gongga
E RKNNAPI: rknn3_init, server connect fail! ret = -1(ERROR_IO)
```

The RKNN3 proxy binary also contains this diagnostic:

```text
kernel need config CONFIG_PCIE_FUNC_RKEP=y
```

Do not spend more time on model conversion or weight transfer until the RK3588
host kernel/runtime package provides `CONFIG_PCIE_FUNC_RKEP=y` or an equivalent
Rockchip RKEP module.

Expected signs after the correct host driver package is installed:

```bash
dmesg | grep pcie-rkep
ls -l /dev/pcie-rkep-*
rknn-smi info
systemctl status rknn3
```

The current Orange Pi host reached the first two expected signs after a custom
RKEP module build:

```text
/usr/lib/modules/pcie-rkep.ko
/dev/pcie-rkep-0000:01:00.0
```

Do not treat RKNN3 service startup as safe yet. The first
`systemctl restart rknn3.service` attempt after installing the M.2 runtime made
the RK3588 host unreachable on `192.168.1.52`.

## Isolation And Recovery State

The following RK1828/RKNN3 files were moved out of live system paths after the
host became unreachable with RK1828 powered:

```text
/usr/lib/modules/pcie-rkep.ko
/bin/rknn3_*
/bin/rknn-smi
/bin/pcie_upgrade_tool
/bin/rknn-console
/bin/rknn-mdns
/bin/rknn_upgrade_tool
/bin/pcie_speed_test_rc
/bin/rkllm3-server
/bin/upgrade_tool
/lib/firmware/rknn3_rk1820.img
/lib/librknn3_api*.so
/lib/librknnsmi.so
/lib/libgstrknnutils.so
/lib/lib*postprocess.so
/lib/aarch64-linux-gnu/gstreamer-1.0/libgstrknn.so
/lib/systemd/system/rknn3.service
/lib/systemd/system/rknn-mdns.service
/etc/udev/rules.d/75-rknn3-coprocessor.rules
/etc/profile.d/rknn3-env.sh
/userdata/aicp_test_aarch64
```

Backup directory:

```text
/home/orangepi/rk1828-rknn3-runtime-disabled-20260703-034331
```

Known-good RK3588-only rollback state from earlier recovery:

```text
rknn3.service: no unit file, inactive
rknn-mdns.service: no unit file, inactive
/usr/lib/modules/pcie-rkep.ko: absent
pcie_rkep: not loaded
RK3588 LAN SSH: reachable at 192.168.1.52
```

Use this state as the baseline for the next power-order test. If RK3588 still
cannot boot when RK1828 is powered first while these files remain isolated, the
failure is unlikely to be caused by RKNN3 service startup. If RK3588 can boot and
enumerate RK1828 in this isolated state, restore runtime pieces one at a time and
test each step manually.

Do not run this until the RK1828-first boot test succeeds on the isolated
baseline:

```bash
sudo systemctl enable --now rknn3.service
```

Preferred staged restore order is:

1. Restore only `/usr/lib/modules/pcie-rkep.ko`.
2. Boot with RK1828 powered first and verify `lspci -nn`.
3. Manually run `sudo insmod /usr/lib/modules/pcie-rkep.ko`.
4. Verify `/dev/pcie-rkep-0000:01:00.0`.
5. Restore user-space RKNN3 tools and libraries.
6. Run `rknn3_transfer_proxy` manually in the foreground.
7. Only after manual checks are stable, consider restoring systemd services.

## Safe Runtime Rule

RK1828 runtime operations must be serialized. Do not run firmware download,
transfer proxy, and model tests at the same time. A bad parallel attempt on
2026-07-03 ran `pcie_upgrade_tool ... uf` and `rknn3_model_test` while
`rknn3_transfer_proxy` was already running; the RK3588 host became unreachable
and showed the red LED state.

Use the guarded wrapper from the Mac control machine for future RK1828 runtime
bring-up:

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

The wrapper takes a remote lock and refuses unsafe combinations:

- `firmware` refuses to run while `rknn3_transfer_proxy` is active.
- `vision-smoke` refuses to run unless the proxy is already active.
- model tests refuse to run while upgrade/model/server processes are present.
- `status` does not invoke `rknn3_transfer_proxy`; use it first after a board
  recovery to check host state without touching the RK1828 runtime path.
- `preflight` also avoids transfer-layer calls; use it after `status` to collect
  PCIe, module, firmware, runtime binary, service, and smoke-file evidence.
- `devices` is the first transfer-layer query and should only be used after both
  `status` and `preflight` show no conflicting runtime processes.
- `pcie-list` runs `pcie_upgrade_tool ld` only. It does not download firmware.
- `smi` runs read-only `rknn-smi` queries with timeouts. If this fails while
  `devices` succeeds, the PCIe/RKEP path is open but RKNN3 device management is
  not initialized.

The wrapper refuses firmware download by default because it can hang the host.
Only use it with physical access to power-cycle the boards:

```bash
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py firmware --allow-firmware-risk
```

Do not bypass this wrapper with hand-written SSH one-liners unless the command is
strictly read-only.

## First Checks After 12V Power

Run these from the Mac control machine before trying model inference:

```bash
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py status
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py preflight
```

Only if both read-only checks look clean, use the first transfer-layer query:

```bash
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py devices
```

Record the output in a new experiment note under `docs/experiments/`.

## Artifact Integrity Check

On the home server, verify the metadata still matches the bundle:

```bash
cd /home/wq/edge-model-lab/models/artifacts/rk1828/qwen3-vl-4b
sha256sum \
  vision/Qwen3-VL-4B-vision-rk1828-prune.rknn \
  vision/Qwen3-VL-4B-vision-rk1828-prune.weight \
  llm/Qwen3-VL-4B-llm-rk1828.rknn \
  llm/Qwen3-VL-4B-llm-rk1828.weight \
  llm/Qwen3-VL-4B-llm.config.pkl \
  llm/Qwen3-VL-4B-llm.tokenizer.gguf \
  llm/Qwen3-VL-4B-llm.embed.bin
```

Compare with `models/artifacts/rk1828/qwen3-vl-4b/manifest.yaml`.

## Host Runtime Setup

Use the RKNN3 SDK materials under:

```text
/Users/wq/Downloads/开发资料/05_RKNN3软件SDK_V1.0.4
```

Relevant local documents:

```text
01_ReleaseNote与QuickStart_V1.0.4/01_Rockchip_RKNPU3_Quick_Start_RKNN3_SDK_V1.0.4_CN.pdf
02_UserGuide与API参考_V1.0.4/02_Rockchip_RKNPU3_User_Guide_RKNN3_SDK_V1.0.4_CN.pdf
03_设备使用与大模型指导/瑞芯微3588&&rk1828设备大模型使用指导-通用版.pdf
03_设备使用与大模型指导/瑞芯微3588&&rk1828设备-两个模组使用指导.pdf
```

Install runtime packages from the RK1820/RK1828 release that matches RKNN3 SDK `1.0.4`. Do not mix RKNN Lite 2 / RKLLM runtime files with RKNN3 runtime files unless the vendor guide explicitly says to.

The local download note points to the vendor packages:

```text
/Users/wq/Downloads/开发资料/05_RKNN3软件SDK_V1.0.4/04_模型资源与获取/下载链接.txt
RK3588_EVB10/RELEASE_V1.0.4
RK1820_RK1828/RELEASE_V1.0.4
```

As of 2026-07-03, the local extracted tree did not contain those release
packages, but the Lenovo Box links were not actually password protected. The
folder metadata API exposes:

```text
RK1820_RK1828/RELEASE_V1.0.4/RK1820_RK1828_M2/rknn3_rk182x_m2_installer_arm64.tgz
RK3588_EVB10/RELEASE_V1.0.4/Linux/Debian/boot.img
RK3588_EVB10/RELEASE_V1.0.4/Linux/Debian/rootfs.img
```

Downloaded local cache:

```text
/Users/wq/edge-model-lab/.cache/rk1828-release-v1.0.4/rknn3_rk182x_m2_installer_arm64.tgz
/Users/wq/edge-model-lab/.cache/rk3588-evb10-release-v1.0.4/boot.img
/Users/wq/edge-model-lab/.cache/rk3588-evb10-release-v1.0.4/rootfs.img
```

The EVB10 `boot.img` contains a Linux `6.1.162` config with:

```text
CONFIG_PCIE_FUNC_RKEP=m
```

This confirms the official RK3588 EVB10 host image carries RKEP as a kernel
module. The module itself is in the EVB10 Debian rootfs, not in the RK1828 M.2
installer tarball:

```text
/usr/lib/modules/pcie-rkep.ko
filename: pcie-rkep.ko
description: Rockchip pcie-rkep demo function driver
name: pcie_rkep
vermagic: 6.1.162 SMP mod_unload aarch64
```

Do not install that EVB10 `.ko` directly on the Orange Pi host. The current
Orange Pi kernel is `6.1.43-rockchip-rk3588`, so the EVB10 `6.1.162` module is
not ABI-matched.

One hidden but important local clue is in:

```text
/Users/wq/Downloads/开发资料/05_RKNN3软件SDK_V1.0.4/05_ASR使用指导/rk1.0.4版本中asr使用指导.pdf
```

Its `driver.sh` section shows the intended board-side install flow:

```bash
apt update && apt install -y build-essential
cd pcie-rkep
make
scp ./pcie-rkep.ko /usr/lib/modules/pcie-rkep.ko
cd ..
tar -zxvf rknn3_rk182x_m2_installer_arm64.tgz && bash install.sh && sync
reboot
```

That means the missing files are specifically:

```text
pcie-rkep/
rknn3_rk182x_m2_installer_arm64.tgz
```

The M.2 installer tarball is now found and cached. It contains `rknn-smi`,
`rknn3_transfer_proxy`, firmware, udev rules, and services, but it does not
contain `pcie-rkep.ko`.

The Rockchip `develop-6.1` kernel tree does contain the RKEP source:

```text
drivers/misc/rockchip/pcie-rkep.c
drivers/misc/rockchip/Kconfig: config PCIE_FUNC_RKEP
drivers/misc/rockchip/Makefile: obj-$(CONFIG_PCIE_FUNC_RKEP) += pcie-rkep.o
```

The Orange Pi kernel source also contains the same driver on branch
`orange-pi-6.1-rk35xx`. The currently installed Orange Pi package is:

```text
linux-image-current-rockchip-rk3588 1.0.8
Linux orangepi5plus 6.1.43-rockchip-rk3588 #1.0.8
```

Orange Pi build commit `55155f1d73cca3cf6bf42a03d7d16df2b14e8014`
introduced `REVISION="1.0.8"` for `orangepi5plus` current images and points to
`KERNELBRANCH='branch:orange-pi-6.1-rk35xx'`. A matching kernel-source
candidate on that branch is commit `752c0d0a12fdce201da45852287b48382caa8c0f`
from 2024-02-03; its top-level Makefile is `VERSION=6`, `PATCHLEVEL=1`,
`SUBLEVEL=43`.

Its Kconfig dependencies are `PCI` and `ARCH_ROCKCHIP`, and it selects
`PCIE_DW_DMATEST`. The current Orange Pi kernel has modules enabled and does not
use `CONFIG_MODVERSIONS`, but it does not ship `/lib/modules/$(uname -r)/build`
or the matching headers. The next runtime-enablement step is therefore building
`pcie-rkep.ko` from the matching Orange Pi `6.1.43-rockchip-rk3588` build tree,
or booting a complete host image/kernel that already includes
`CONFIG_PCIE_FUNC_RKEP`.

Do not build against Orange Pi branch HEAD without checking the version first:
as of this inspection, branch HEAD is `6.1.99`, which will not match the running
`6.1.43-rockchip-rk3588` kernel.

The successful module build used:

```text
/home/wq/edge-tools/orangepi-kernel/linux-orangepi-6.1.43-full
git commit: 752c0d0a12fdce201da45852287b48382caa8c0f
```

Build changes relative to the Orange Pi 6.1.43 source:

```text
CONFIG_LOCALVERSION="-rockchip-rk3588"
# CONFIG_LOCALVERSION_AUTO is not set
CONFIG_PCIE_DW_DMATEST=y
CONFIG_PCIE_FUNC_RKEP=m
MODULE_DEVICE_TABLE(pci, pcie_rkep_pcidev_id);
{ PCI_VDEVICE(ROCKCHIP, 0x182a), 1,  },
```

Verified module metadata:

```text
alias:    pci:v00001D87d0000182Asv*sd*bc*sc*i*
vermagic: 6.1.43-rockchip-rk3588 SMP mod_unload aarch64
```

Verified manual load on RK3588 before RKNN3 startup:

```text
insmod_rc=0
crw------- 1 root root 10, 120 /dev/pcie-rkep-0000:01:00.0
pcie-rkep 0000:01:00.0: did=182a
```

The RK1828 M.2 runtime installer has been installed on the RK3588 host, but
`rknn3.service` startup caused the host to stop responding. On the next boot,
disable or inspect `rknn3.service` before starting it again.

Public RK182x bring-up notes support the same diagnosis:

- RK182X is documented as a coprocessor used with RK3588/RK3576 over PCIe/USB,
  with board-side drivers providing the RK182X PCIe EP path.
- Known-good RK3588 + RK182x notes enable `CONFIG_PCIE_FUNC_RKEP=y` and
  `CONFIG_PCIE_DW_DMATEST=y`, then validate with `/dev/pcie-rkep*` and
  `rknn-smi info`.
- One public note also states the same physical order observed here: power the
  accelerator card first, then power the RK3588 board.

Use public notes only as diagnosis references. Do not directly boot a kernel
built for another vendor board on the Orange Pi. The safe path is either a
Rockchip/FAE RK3588 host package for RK1828, or an Orange Pi kernel rebuild with
the required Rockchip RKEP support and a rollback plan.

## Conversion Record

The conversion used RKNN3 Toolkit `1.0.4`.

Vision and LLM RKNN exports both completed. The LLM log ended with:

```text
RKNN Compiler All stages completed successfully
```

The cleaned-up command record is in:

```text
docs/experiments/2026-07-02-rk1828-qwen3-vl-4b-rknn3-conversion.md
```

## Done Criteria

RK1828 can be marked as runtime-ready only after all of these are true:

1. RK1828 has separate 12V power.
2. RK3588 detects the RK1828 hardware.
3. RK3588 host kernel exposes the Rockchip RKEP PCIe transfer path.
4. RKNN3 runtime libraries and drivers load without errors.
5. The vision RKNN3 artifact loads.
6. The LLM RKNN3 artifact plus `.weight`, `.config.pkl`, tokenizer, and embed files load.
7. A small multimodal prompt returns a plausible answer.
8. The experiment note records commands, output, power setup, and any thermal observations.
