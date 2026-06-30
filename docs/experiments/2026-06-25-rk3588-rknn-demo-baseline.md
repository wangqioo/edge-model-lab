# RK3588 RKNN Demo Baseline

## Goal

Start M2 by validating the built-in RKNN demo on `orange-rk3588` without changing device state.

## Target Device

- `orange-rk3588`
- Hostname: `orangepi5plus`
- OS: Orange Pi 1.2.0 Bookworm
- Kernel: `6.1.43-rockchip-rk3588`

## Pre-Run Health Snapshot

`./scripts/edgectl health orange-rk3588` succeeded.

Relevant state:

- Docker 27.3.1 present.
- containerd 1.7.23 present.
- Python 3.11.2 and pip 23.0.1 present.
- RKNN files present:
  - `/usr/bin/rknn_demo`
  - `/usr/bin/rknn_server`
  - `/usr/lib/librknn_api.so`
  - `/usr/lib/librknnrt.so`
  - `/usr/share/rknn_demo/mobilenet_ssd.rknn`
- One failed systemd unit remains: `smartmontools.service`.

## Demo Entrypoint Inspection

`/usr/local/bin/test_rknn_demo.sh` exists, but it is not safe as a first headless baseline because it:

- sets all CPU governors to `performance`,
- stops `lightdm`,
- starts `/usr/bin/npu_transfer_proxy`,
- launches `rknn_demo` camera preview.

Because the project is still in read-only baseline mode, this script was not run.

## Attempted Non-Invasive Demo Check

Commands:

```bash
timeout 5 /usr/bin/rknn_demo --help
timeout 5 /usr/bin/rknn_demo -h
ldd /usr/bin/rknn_demo
```

Result:

`rknn_demo` did not start. The dynamic linker failed before help output:

```text
/usr/bin/rknn_demo: error while loading shared libraries: libdrm.so.2: cannot open shared object file: No such file or directory
```

`ldd /usr/bin/rknn_demo` also reported missing runtime libraries:

```text
libdrm.so.2 => not found
librga.so => not found
libfreetype.so.6 => not found
libpixman-1.so.0 => not found
librockchip_mpp.so.1 => not found
```

Package inspection showed Debian candidates exist for:

- `libdrm2`
- `libfreetype6`
- `libpixman-1-0`

No installed package currently provides the missing libraries found by `ldd`.

## Cleanup

A stale `rknn_server --version` process from the earlier audit was found:

```text
rknn_server --version
```

It was killed because it was created by the previous audit command and was still running.

## Result

M2 RK3588 RKNN demo is blocked by missing shared libraries. This is a useful baseline result: the board has RKNN demo artifacts and runtime files, but the demo package is not currently runnable as installed.

## Next Task

Create a controlled remediation step for `orange-rk3588`:

1. Install missing Debian runtime packages:
   - `libdrm2`
   - `libfreetype6`
   - `libpixman-1-0`
2. Locate or install Rockchip-specific packages/libraries for:
   - `librga.so`
   - `librockchip_mpp.so.1`
3. Re-run `ldd /usr/bin/rknn_demo`.
4. Only after all libraries resolve, run a bounded demo command.

Do not run `/usr/local/bin/test_rknn_demo.sh` until the project explicitly allows temporary display/session changes.

