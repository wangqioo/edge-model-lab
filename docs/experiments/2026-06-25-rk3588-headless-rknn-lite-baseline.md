# RK3588 Headless RKNN Lite Baseline

## Goal

Create a headless RKNN Lite baseline on `orange-rk3588` without using the MiniGUI camera preview demo.

## Target Device

- Device ID: `orange-rk3588`
- Hostname: `orangepi5plus`
- Python: 3.11.2
- Kernel: `6.1.43-rockchip-rk3588`

## Environment Created

Created board-local virtual environment:

```text
/home/orangepi/edge-model-lab/venv
```

Installed packages:

```text
pip 26.1.2
setuptools 82.0.1
wheel 0.47.0
numpy 2.4.6
pillow 12.2.0
psutil 7.2.2
ruamel.yaml 0.19.1
rknn-toolkit-lite2 2.3.0
```

Note: `rknn-toolkit-lite2` 2.3.2 was tested first, then 2.3.0 was tested because 2.3.2 rejected explicit `target="rk3588"` with the same platform error. Both versions behave the same for explicit target initialization.

## Import Check

This passed:

```python
from rknnlite.api import RKNNLite
import numpy as np
import PIL
```

Observed:

```text
RKNNLite import ok <class 'rknnlite.api.rknn_lite.RKNNLite'>
numpy 2.4.6
pillow 12.2.0
```

## Runtime Library Upgrade

The board initially had:

```text
librknnrt version: 1.4.0 (a10f100eb@2022-09-09T09:07:14)
```

Downloaded official aarch64 runtime from:

```text
https://raw.githubusercontent.com/airockchip/rknn-toolkit2/master/rknpu2/runtime/Linux/librknn_api/aarch64/librknnrt.so
```

Backed up the old runtime:

```text
/usr/lib/librknnrt.so.backup-20260625014518
```

Installed the new runtime:

```text
/usr/lib/librknnrt.so
```

Verified:

```text
librknnrt version: 2.3.2 (429f97ae6b@2025-04-09T09:09:27)
```

`ldconfig` warned that `/lib/librknnrt.so` is not a symbolic link. This warning existed because the runtime is installed as a direct shared object, not a symlink chain. The runtime is still loadable.

## Probe Script

Created:

```text
/home/orangepi/edge-model-lab/rknn_probe.py
```

Probe behavior:

1. load `/usr/share/rknn_demo/mobilenet_ssd.rknn`
2. call `init_runtime(target="rk3588")`
3. release runtime

Model load succeeds:

```text
load_ret 0
```

Explicit target runtime init fails in both RKNN Lite 2.3.2 and 2.3.0:

```text
Exception: Unsupported run platform: Linux aarch64
init_ret -1
```

## Variant Probe

Created:

```text
/home/orangepi/edge-model-lab/rknn_probe_variants.py
```

Tested:

- `init_runtime(target="rk3588")`
- `init_runtime(target="RK3588")`
- `init_runtime()`
- `LIBRKNNRT_PATH=/usr/lib/librknnrt.so` with explicit target

Result:

- explicit target variants still fail with `Unsupported run platform: Linux aarch64`
- no-target variant reaches RKNN runtime and driver, but rejects the bundled model

Runtime/driver observed:

```text
RKNN Runtime Information, librknnrt version: 2.3.2 (429f97ae6b@2025-04-09T09:09:27)
RKNN Driver Information, version: 0.9.6
```

Bundled model failure:

```text
Verify ModelBuffer failed!
Invalid RKNN format
Import rknn model failed!
RKNN init failed. error code: RKNN_ERR_MODEL_INVALID
```

## Result

Headless RKNN Lite is installed and importable. The board can load RKNN Lite Python modules and the updated RKNN runtime reaches the NPU driver when `init_runtime()` is called without explicit target.

The remaining blocker is model artifact compatibility:

- local `/usr/share/rknn_demo/mobilenet_ssd.rknn` loads through RKNN Lite file parsing,
- but RKNN Runtime 2.3.2 rejects it as invalid at runtime initialization.

There is no other `.rknn` model on the board.

## Next Action

Generate or obtain a RK3588-compatible `.rknn` model using RKNN Toolkit2 2.3.x, then rerun the same headless probe.

Preferred next task:

1. Install full `rknn-toolkit2` on the Mac or an x86 Linux conversion environment.
2. Convert a small known ONNX model to RK3588 with toolkit 2.3.x.
3. Copy the generated `.rknn` to `orange-rk3588`.
4. Run `init_runtime()` and one inference pass through RKNN Lite.

Alternative:

Install `rknn-toolkit2` in the Orange Pi venv and attempt conversion on-board. This is less ideal because conversion workloads are better done off-device, but the package is visible from the configured Python index.

