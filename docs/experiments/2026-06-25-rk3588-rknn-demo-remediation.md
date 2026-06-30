# RK3588 RKNN Demo Remediation

## Goal

Fix the missing shared-library blockers found in the first RK3588 RKNN demo baseline, then run bounded demo probes.

## Target Device

- Device ID: `orange-rk3588`
- Hostname: `orangepi5plus`
- User: `orangepi`

## Changes Made

Installed standard Debian runtime libraries:

```text
libdrm-common 2.4.114-1
libdrm2:arm64 2.4.114-1+b1
libfreetype6:arm64 2.12.1+dfsg-5+deb12u4
libpixman-1-0:arm64 0.42.2-1
```

Installed Rockchip MPP runtime:

```text
librockchip-mpp1 1.5.0-1
```

Source:

```text
https://mirror.nju.edu.cn/radxa-deb/rk3588-bookworm-test/pool/main/m/mpp/librockchip-mpp1_1.5.0-1_arm64.deb
```

Installed RGA runtime from upstream airockchip prebuilt Linux aarch64 artifact:

```text
/usr/local/lib/rockchip-rga/librga.so
/etc/ld.so.conf.d/rockchip-rga.conf
```

Source:

```text
https://github.com/airockchip/librga
libs/Linux/gcc-aarch64/librga.so
```

Then ran:

```bash
sudo /sbin/ldconfig
```

## Verification

Final `ldd /usr/bin/rknn_demo` reported no missing shared libraries.

Relevant resolved libraries:

```text
librknn_api.so => /lib/librknn_api.so
libdrm.so.2 => /lib/aarch64-linux-gnu/libdrm.so.2
librga.so => /usr/local/lib/rockchip-rga/librga.so
libfreetype.so.6 => /lib/aarch64-linux-gnu/libfreetype.so.6
libpixman-1.so.0 => /lib/aarch64-linux-gnu/libpixman-1.so.0
librockchip_mpp.so.1 => /lib/aarch64-linux-gnu/librockchip_mpp.so.1
```

`ldconfig -p` now includes:

```text
librockchip_mpp.so.1 => /lib/aarch64-linux-gnu/librockchip_mpp.so.1
librga.so => /usr/local/lib/rockchip-rga/librga.so
```

## Demo Probe Result

After shared-library remediation, bounded demo probes start the binary but fail during MiniGUI initialization:

```text
MISC: Can not locate your MiniGUI.cfg file or bad files!
KERNEL>InitGUI: Initialization of misc things failure!
success build
```

Observed for:

```bash
timeout 8 /usr/bin/rknn_demo --help
timeout 8 /usr/bin/rknn_demo -h
timeout 8 /usr/bin/rknn_demo
```

The built-in script `/usr/local/bin/test_rknn_demo.sh` still was not run because it changes runtime state:

- sets CPU governors to `performance`,
- stops `lightdm`,
- starts `/usr/bin/npu_transfer_proxy`,
- launches a camera preview.

## Additional Findings

No headless RKNN CLI was found beyond:

```text
rknn_demo
rknn_camera
rknn_server
start_rknn.sh
restart_rknn.sh
test_rknn_demo.sh
```

Python runtime packages are still missing:

```text
rknnlite: missing
rknn: missing
numpy: missing
cv2: missing
```

Temperatures after bounded probes were normal:

```text
soc-thermal 36.1 C
bigcore0-thermal 35.2 C
bigcore1-thermal 35.2 C
littlecore-thermal 36.1 C
center-thermal 35.2 C
gpu-thermal 35.2 C
npu-thermal 35.2 C
```

No persistent `rknn_demo`, `npu_transfer`, or `rknn_server` process remained after the probes.

## Result

Runtime linking for `/usr/bin/rknn_demo` is fixed. The built-in GUI demo is now blocked by missing MiniGUI config/resources, not missing shared libraries.

## Next Action

Do not chase the MiniGUI camera-preview demo as the primary baseline. For edge model deployment validation, the next useful step is a headless RKNN Lite baseline:

1. Install Python runtime packages on `orange-rk3588`.
2. Install an RKNN Lite 2 wheel compatible with RK3588/aarch64/Python 3.11.
3. Run a minimal headless inference against `/usr/share/rknn_demo/mobilenet_ssd.rknn`.
4. Record latency, memory, temperature, and any NPU driver errors.

