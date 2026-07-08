# RK1828K Vendor Escalation Report

Date: 2026-07-08

## Summary

The RK1828K M.2 accelerator is visible to the RK3588 host over PCIe, and the
RKEP driver plus RKNN3 SMI userspace can open the PCIe device. The unresolved
failure is the RK1828K endpoint becoming not alive / the RK3588 host becoming
unreachable when the official RKNN3 startup path downloads firmware.

Vendor-recommended startup delays were applied to both `/bin/rknn3_startup` and
`/usr/bin/rknn3_startup`:

```sh
sleep 2   # after driver load
sleep 10  # after firmware update
```

Retesting the delayed startup script still made the RK3588 host unreachable.

## Hardware And Power State

- Host: Orange Pi 5 Plus / RK3588
- OS: Orange Pi 1.2.0 Bookworm
- Kernel: `Linux orangepi5plus 6.1.43-rockchip-rk3588 #1.0.8 SMP Tue Apr 1 13:54:00 CST 2025 aarch64`
- Accelerator: RK1828K M.2 board over PCIe
- Power: separate 12 V supply connected directly to the RK1828K carrier board
- Power wiring issue was found and corrected earlier; the current failure was
  reproduced after the power polarity and supply capacity were corrected.

## Installed Runtime Versions

Runtime package:

```text
rknn3_rk182x_m2_installer_arm64.tgz
sha256: 55dccda3daec644886f807e5f4b8616f1a9236c86a1adacddc17a9ae939c944a
```

The vendor later provided this archive:

```text
/Users/wq/Desktop/rknn_install_without_model(1).tar.gz
sha256: 1a5ad33cc7cf945621a6046a52f63b7198fbee2f66cd75e0f4aa77a8ad5ad752
```

Contents:

```text
rknn/driver/driver-rknn.sh
rknn/driver/driver-ubuntu.sh
rknn/driver/pcie-rkep/pcie-rkep.c
rknn/driver/pcie-rkep/rk-pcie-ep.h
rknn/driver/rknn3_rk182x_m2_installer_arm64.tgz
```

The inner installer is byte-for-byte the same package already tested:

```text
55dccda3daec644886f807e5f4b8616f1a9236c86a1adacddc17a9ae939c944a  vendor/rknn3_rk182x_m2_installer_arm64.tgz
55dccda3daec644886f807e5f4b8616f1a9236c86a1adacddc17a9ae939c944a  previous/rknn3_rk182x_m2_installer_arm64.tgz
```

The firmware inside it is also identical:

```text
83807abd6e068e52fdd27436d9e06a9db9d9e69d285b1c1379fa16ab3fe1e884  rknn3_rk1820.img
```

Important driver-source finding:

```c
/* rknn/driver/pcie-rkep/pcie-rkep.c */
#define DRV_VERSION 0x00030300
```

This conflicts with the earlier `rknn-smi` debug finding that RKNN3 userspace
requires at least driver version `0x30301`:

```text
pcie_rkep drv version 0x0 is not compatible, at least 0x30301
```

Therefore the supplied `driver-ubuntu.sh` should not be run blindly on the
current RK3588 host. It compiles the vendor `pcie-rkep` source and installs it
to `/usr/lib/modules/pcie-rkep.ko`, then installs the same runtime package and
reboots. With the source as provided, this may downgrade the driver ABI back to
`0x30300`, which is below the RKNN3 userspace requirement already observed.

The vendor script was then executed exactly as provided on the RK3588 host after
backing up the live driver, startup scripts, and firmware:

```text
backup=/root/rknn-vendor-backup-20260708-132008
```

The archive uploaded to the board matched the vendor file:

```text
1a5ad33cc7cf945621a6046a52f63b7198fbee2f66cd75e0f4aa77a8ad5ad752  rknn_install_without_model.tar.gz
```

Precheck on the board:

```text
Linux orangepi5plus 6.1.43-rockchip-rk3588 #1.0.8 SMP Tue Apr 1 13:54:00 CST 2025 aarch64 GNU/Linux
ls: cannot access '/usr/src/linux-headers-6.1.43-rockchip-rk3588': No such file or directory
ls: cannot access '/lib/modules/6.1.43-rockchip-rk3588/build': No such file or directory
pcie-rkep/pcie-rkep.c:37:#define DRV_VERSION 0x00030300
```

Exact vendor script result:

```text
[1/5] 更新系统并安装 build-essential...
build-essential is already the newest version (12.9).

[2/5] 编译 pcie-rkep 驱动...
make -C /usr/src/linux-headers-`uname -r`/ M=/tmp/rknn_vendor_install_run/rknn/driver/pcie-rkep modules
make[1]: *** /usr/src/linux-headers-6.1.43-rockchip-rk3588/: No such file or directory.  Stop.
make: *** [Makefile:13: modules] Error 2
VENDOR_SCRIPT_FAILED_OR_REBOOTED=2
```

The script stopped at driver compilation and did not reach the runtime install
or reboot steps. The host stayed reachable afterward, and the live files were
unchanged:

```text
10 packets transmitted, 10 packets received, 0.0% packet loss
pcie_rkep loaded
/usr/lib/modules/pcie-rkep.ko size: 214768 bytes
/bin/rknn3_startup size: 1765 bytes
/lib/firmware/rknn3_rk1820.img size: 3371537 bytes
rknn-smi info -> Device 0 Offline
```

Local execution log:

```text
tmp/rknn-vendor-full-install-real-20260708-132004.log
```

Installed files on RK3588 host:

```text
83807abd6e068e52fdd27436d9e06a9db9d9e69d285b1c1379fa16ab3fe1e884  /lib/firmware/rknn3_rk1820.img
659f4c61d390ed7cb58c01d29bfbec24b200455957fb49447dfb65288bf3f1ab  /bin/rknn-smi
87ce12b9ed19e200ba747b797cf195de3c4635f3c12464b39907ae45d4b7a9cc  /bin/pcie_upgrade_tool
ea88b16e41d4dbbfa39793ac87862f2f43faee877dea07c0842cad7bd45e5ddd  /bin/rknn3_transfer_proxy
2343ebd6bf3826e3f1da747b3101826522ade509112725b26a4559f2dd9d16df  /usr/lib/modules/pcie-rkep.ko
```

Tool versions:

```text
PCIe Upgrade Tool v1.2.1
rknn-smi version: 1.3.0
rknn3 API version: 1.0.4
```

## Current Safe Baseline

After booting with RK1828K powered first, the host detects the device:

```text
0000:01:00.0 Processing accelerators [1200]: Rockchip Electronics Co., Ltd Device [1d87:182a] (rev 01)
0000:01:00.0 0x1d87 0x182a 0x120000
```

Driver and device node:

```text
pcie_rkep loaded
/dev/pcie-rkep-0000:01:00.0 exists
```

`pcie_upgrade_tool td` succeeds:

```text
Program directory: /usr/bin/
Testing device...
Soc=rk1820 Addr=0000:01:00.0 Mode=MaskROM [1d87:182a]
Testing device OK
```

`rknn3_transfer_proxy devices` sees the PCIe device:

```text
List of ntb devices attached
0000:01:00.0        b98e6c51    PCIE
```

`rknn-smi info` no longer fails initialization. It sees one PCIe device, but the
device is offline:

```text
Device Count: 1
Communication mode: PCIe
Product Name: NA
Serial Number: NA
Chip Count: 0

Device 0 Status: Offline
Health: NA
Power: NA
Temp: NA
Memory: NA / NA
```

Relevant SMI debug log:

```text
open rkep: /dev/pcie-rkep-0000:01:00.0 Success.
id=182a1d87
magic=18, ver=49f76a3c
rc_cc_version=30301
ep_cc_version=5bedd9db
gen2x1
hw_reset, 18, 17
PCIe device 0 is not alive
Total EP device num: 1
rknnsmi init success
Device id: 0 is not alive, failed
```

## Vendor Delay Test

The seller suggested adding startup delays to `rknn3_startup`. This was applied
on the host:

```sh
# edge-model-lab: wait after driver load per vendor guidance
sleep 2

# edge-model-lab: wait after firmware update per vendor guidance
sleep 10
```

Both `/bin/rknn3_startup` and `/usr/bin/rknn3_startup` contain these delays.
`rknn3.service` and `rknn-mdns.service` are disabled, so the startup script was
run manually.

Command:

```bash
/bin/rknn3_startup stop
/bin/rknn3_startup start
```

Observed output:

```text
start:open rknn3_transfer_proxy
find device 0000:01:00.0
Timeout, server 192.168.1.52 not responding.
SSH_STARTUP_COMMAND_FAILED=255
```

Immediate ping after the command:

```text
ping: sendto: Host is down
6 packets transmitted, 0 packets received, 100.0% packet loss
ssh: connect to host 192.168.1.52 port 22: Host is down
```

Conclusion from this test: adding the requested delays did not fix the firmware
download / endpoint alive failure. The host still becomes unreachable during or
immediately after the startup script launches:

```text
pcie_upgrade_tool -s 0000:01:00.0 uf /lib/firmware/rknn3_rk1820.img
```

The full local log is:

```text
tmp/rk1828-vendor-startup-20260708-093211.log
```

## Firmware Image Inspection

The supplied M.2 installer contains only this firmware:

```text
system_root/lib/firmware/rknn3_rk1820.img
```

The image was unpacked locally. RKFW/RKAF contents:

```text
BOOT
sha256: 6dac3fec660fa5720c81a0850b793ca5be1e010e0574df3c428e8465268e4bea

embedded-update.img
sha256: 5d53b00dc4383689b732635a7b91fd48cfee91cb10245bf15373e59fdc996dff

rk1820_ddr_v1.15.bin
sha256: 1f1cf1232146501e112c8dc94f1337852fe49c7aae0d1fea876454711ae03767
```

RKAF partition metadata:

```text
parameter,parameter.mem,0x02400400,0x00000000,0x00000800,0x00000001,0x00000179
subsoc_os,subsoc_rtt.img,0x00004000,0x02a00400,0x00001000,0x00000502,0x00280a20
node2_os,node2_rtt.img,0x00004000,0x02400400,0x00282000,0x000000f1,0x00078020
node4_os,node4_rtt.img,0x00004000,0x02800400,0x002fa800,0x0000003e,0x0001e820
ddr,rk1820_ddr_v1.15.bin,0x00000100,0x08200008,0x00319800,0x0000000e,0x00006dd0
```

Strings inside the image include:

```text
RK1820
MACHINE_MODEL: RK1820
MANUFACTURER: RK1820
rk1820_ddr_v1.15.bin
```

No explicit `RK1828K` string was found in the supplied firmware image or local
documentation. This does not by itself prove the image is wrong, because the
vendor may package RK182X firmware under RK1820 naming. It does require explicit
vendor confirmation.

## Bootloader-Only Isolation

The `BOOT` payload extracted from `rknn3_rk1820.img` was copied to the RK3588
host as `/tmp/rk1828-fw/BOOT`.

Command:

```bash
pcie_upgrade_tool -s 0000:01:00.0 db /tmp/rk1828-fw/BOOT
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

The RK3588 host stayed reachable during bootloader-only download. This narrows
the failure to the stage after Loader starts: full firmware/DDR/RTT download,
Loader protocol, or PCIe DMA/message setup after Loader mode.

After a later reboot, `/tmp/rk1828-fw/BOOT` had to be copied again because it
lives under `/tmp`. Repeating the test produced the same Loader result:

```text
sha256(/tmp/rk1828-fw/BOOT)=6dac3fec660fa5720c81a0850b793ca5be1e010e0574df3c428e8465268e4bea

pcie_upgrade_tool -s 0000:01:00.0 td
Soc=rk1820 Addr=0000:01:00.0 Mode=MaskROM [1d87:182a]
Testing device OK

pcie_upgrade_tool -s 0000:01:00.0 db /tmp/rk1828-fw/BOOT
Downloading bootloader OK

pcie_upgrade_tool -s 0000:01:00.0 td
Soc=rk1820 Addr=0000:01:00.0 Mode=Loader [1d87:182a]
Testing device OK
```

Then `rd` was tested from Loader mode:

```text
pcie_upgrade_tool -s 0000:01:00.0 rd
Device reset OK

pcie_upgrade_tool -s 0000:01:00.0 td
Soc=rk1820 Addr=0000:01:00.0 Mode=Loader [1d87:182a]
Testing device OK
```

So `rd` returns success in Loader mode and does not hang the host, but it did
not bring the endpoint back to MaskROM in this test.

## Full Firmware From Loader

Starting from the confirmed Loader state, full firmware download was tested
without `rknn3_transfer_proxy`, using an explicit temporary directory:

```bash
pcie_upgrade_tool -s 0000:01:00.0 uf /lib/firmware/rknn3_rk1820.img /tmp/rk1828-fw
```

Observed result:

```text
Timeout, server 192.168.1.52 not responding.
UF_SSH_FAILED=255

8 packets transmitted, 0 packets received, 100.0% packet loss
ssh: connect to host 192.168.1.52 port 22: Operation timed out
```

Local log:

```text
tmp/rk1828-loader-uf-direct-20260708-094412.log
```

This means the failure is not only caused by the startup script or by skipping
the bootloader stage. Even after `db BOOT` succeeds and `td` reports
`Mode=Loader`, `uf rknn3_rk1820.img` still makes the RK3588 host unreachable.

Unsafe observed after entering Loader:

```text
pcie_upgrade_tool uf /lib/firmware/rknn3_rk1820.img /tmp/rk1828-fw
pcie_upgrade_tool rvd ...
rknn-smi / SMI-style interaction
```

Those interactions caused the RK3588 host to become unreachable in previous
tests.

## Questions For Vendor

Please confirm:

1. Is `rknn3_rk1820.img` from `rknn3_rk182x_m2_installer_arm64.tgz` the correct
   firmware for RK1828K M.2 hardware?
2. Does RK1828K require a dedicated RK1828K `update.img`, `loader.bin`, DDR
   firmware, or runtime package?
3. In the newly provided `rknn_install_without_model(1).tar.gz`, why does
   `pcie-rkep.c` declare `DRV_VERSION 0x00030300` when RKNN3 userspace requires
   at least `0x30301`?
4. Should the vendor driver source be patched to `0x00030301` before compiling
   for Orange Pi 5 Plus, or is there a newer driver source package?
5. Please provide the exact Orange Pi 5 Plus / RK3588 kernel headers or kernel
   source tree required by `driver-ubuntu.sh`, because the board does not have
   `/usr/src/linux-headers-6.1.43-rockchip-rk3588` or
   `/lib/modules/6.1.43-rockchip-rk3588/build`.
6. What is the correct RK1828K PCIe boot sequence on RK3588?
   For example, should we run `db loader.bin` first, then `uf firmware`, then
   `run`, or should `uf rknn3_rk1820.img` be sufficient?
7. What do these SMI/RKEP values mean?
   `magic=18, ver=49f76a3c`, `ep_cc_version=5bedd9db`, `hw_reset, 18, 17`.
8. Is Orange Pi 5 Plus kernel `6.1.43-rockchip-rk3588 #1.0.8` supported with
   this RK1828K M.2 card and the supplied `pcie-rkep.ko`?
9. If the above package is correct, what further logs should be captured before
   firmware download, given that the host becomes unreachable immediately after
   `find device 0000:01:00.0`?

## Copy-Paste Message For Seller

```text
我们已经按你们建议修改了 /bin/rknn3_startup 和 /usr/bin/rknn3_startup：
驱动加载后 sleep 2，固件下载后 sleep 10。

现在供电已确认修正，RK1828K 单独 12V 供电，主机为 Orange Pi 5 Plus / RK3588，
系统为 Orange Pi 1.2.0 Bookworm，内核：
Linux orangepi5plus 6.1.43-rockchip-rk3588 #1.0.8 SMP Tue Apr 1 13:54:00 CST 2025 aarch64。

当前安全状态：
lspci 能看到：
0000:01:00.0 Processing accelerators [1200]: Rockchip Electronics Co., Ltd Device [1d87:182a] (rev 01)

/dev/pcie-rkep-0000:01:00.0 存在，pcie_rkep 已加载。

pcie_upgrade_tool -s 0000:01:00.0 td 返回：
Soc=rk1820 Addr=0000:01:00.0 Mode=MaskROM [1d87:182a]
Testing device OK

rknn3_transfer_proxy devices 返回：
0000:01:00.0        b98e6c51    PCIE

rknn-smi info 现在能初始化并看到 1 个 PCIe 设备，但状态是 Offline，Chip Count=0。
debug 里有：
open rkep: /dev/pcie-rkep-0000:01:00.0 Success
id=182a1d87
magic=18, ver=49f76a3c
ep_cc_version=5bedd9db
hw_reset, 18, 17
PCIe device 0 is not alive

但是运行已加延时的 /bin/rknn3_startup start 后，输出到：
start:open rknn3_transfer_proxy
find device 0000:01:00.0
随后 SSH 断开，ping 显示 Host is down，RK3588 整机不可达。
也就是说增加 sleep 2 / sleep 10 后仍然复现掉线。

我们拆包检查了你们给的 rknn3_rk182x_m2_installer_arm64.tgz：
里面固件是 /lib/firmware/rknn3_rk1820.img。
该 img 解包后 RKAF metadata 显示：
manufacturer/model 字符串是 RK1820，
DDR 文件是 rk1820_ddr_v1.15.bin，
没有找到明确 RK1828K 字符串。

你们后来发的 rknn_install_without_model(1).tar.gz 我们也检查了：
里面的 rknn3_rk182x_m2_installer_arm64.tgz 和之前测试过的包 SHA256 完全一样：
55dccda3daec644886f807e5f4b8616f1a9236c86a1adacddc17a9ae939c944a。
里面的 rknn3_rk1820.img 也完全一样：
83807abd6e068e52fdd27436d9e06a9db9d9e69d285b1c1379fa16ab3fe1e884。

新包外层多了 pcie-rkep 驱动源码和 driver-ubuntu.sh，但源码里：
#define DRV_VERSION 0x00030300
而我们之前 rknn-smi debug 明确报过需要至少 0x30301：
pcie_rkep drv version 0x0 is not compatible, at least 0x30301。
请确认这个源码版本是否正确？是否需要提供 DRV_VERSION=0x00030301 或更新版本的 pcie-rkep 源码？
如果直接执行 driver-ubuntu.sh，是否会把驱动 ABI 降级回 0x30300？

我们也按你们给的 driver-ubuntu.sh 原样执行了一遍。压缩包已上传到板子并校验：
1a5ad33cc7cf945621a6046a52f63b7198fbee2f66cd75e0f4aa77a8ad5ad752。

脚本执行到第 2 步编译驱动失败：
make -C /usr/src/linux-headers-`uname -r`/ M=/tmp/rknn_vendor_install_run/rknn/driver/pcie-rkep modules
make[1]: *** /usr/src/linux-headers-6.1.43-rockchip-rk3588/: No such file or directory.  Stop.
make: *** [Makefile:13: modules] Error 2

板子上确实没有：
/usr/src/linux-headers-6.1.43-rockchip-rk3588
/lib/modules/6.1.43-rockchip-rk3588/build

所以你们这个安装步骤在当前 Orange Pi 5 Plus 官方系统上不能完整跑完。
请提供对应内核 headers/source，或者提供已经编译好的、适配
6.1.43-rockchip-rk3588 且 ABI 版本满足 RKNN3 1.0.4 的 pcie-rkep.ko。

单独从 rknn3_rk1820.img 拆出的 BOOT 执行：
pcie_upgrade_tool -s 0000:01:00.0 db /tmp/rk1828-fw/BOOT
可以成功从 MaskROM 进入 Loader：
Soc=rk1820 Addr=0000:01:00.0 Mode=Loader [1d87:182a]
Testing device OK
并且主机不会马上掉线。

从 Loader 状态执行 rd：
pcie_upgrade_tool -s 0000:01:00.0 rd
返回 Device reset OK，但 td 后仍显示 Mode=Loader。

从 Loader 状态继续执行 full firmware：
pcie_upgrade_tool -s 0000:01:00.0 uf /lib/firmware/rknn3_rk1820.img /tmp/rk1828-fw
仍然会导致 SSH 超时、ping 100% 丢包，RK3588 整机不可达。
所以问题不是单纯因为没有先 db BOOT。

Loader 后继续 rvd/SMI 交互也会卡住并导致 RK3588 不可达。

请帮忙确认：
1. rknn3_rk1820.img 是否就是 RK1828K M.2 正确固件？
2. RK1828K 是否需要专用 update.img / loader.bin / DDR 固件 / runtime 包？
3. 你们新发的 pcie-rkep.c 为什么还是 DRV_VERSION 0x00030300？RKNN3 1.0.4 是否要求 0x30301？
4. 是否需要提供新版 pcie-rkep 源码，或者我们应该把 DRV_VERSION 改成 0x00030301 后再编译？
5. 请提供 Orange Pi 5 Plus 当前内核 6.1.43-rockchip-rk3588 对应的 headers/source，或者直接提供编译好的 pcie-rkep.ko。
6. RK3588 + RK1828K PCIe 正确启动流程是什么？是否应该先 db loader.bin，再 uf/run？
7. magic=18, ver=49f76a3c、ep_cc_version=5bedd9db、hw_reset,18,17 分别表示什么？
8. Orange Pi 5 Plus 6.1.43-rockchip-rk3588 是否支持你们这块 RK1828K M.2 和当前 pcie-rkep.ko？
```
