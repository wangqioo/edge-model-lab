# Troubleshooting

## Symptom: `rknpu driver version is too low`

Example:

```text
Warning: Your rknpu driver version is too low
rknpu driver version: 0.9.6
```

Meaning:

The runtime can see the NPU driver, but the driver is older than the RKLLM runtime expects.

Fix used on Orange Pi:

```text
upgrade kernel package to linux-image-current-rockchip-rk3588 1.0.8
RKNPU becomes v0.9.8
```

Verify:

```bash
sudo cat /sys/kernel/debug/rknpu/version
```

Expected:

```text
RKNPU driver: v0.9.8
```

## Symptom: `failed to malloc npu memory`

Example:

```text
failed to malloc npu memory, size: 4022272000
```

Meaning:

The model asks the NPU driver for a large contiguous memory allocation and the board cannot satisfy it.

Check CMA:

```bash
grep -E "CmaTotal|CmaFree" /proc/meminfo
```

For the Orange Pi Qwen3-VL-4B path, known working:

```text
CmaTotal: 3670016 kB
```

Also check the RKNPU version. In this project, CMA alone did not solve the issue until the RKNPU driver was upgraded.

## Symptom: RKLLM works on one board but not another

Likely causes:

1. Wrong chip target: RK3576 artifact on RK3588, or the reverse.
2. Different RKNPU driver version.
3. Different memory size.
4. Different runtime library version.
5. Different boot CMA.

First checks:

```bash
uname -a
sudo cat /sys/kernel/debug/rknpu/version
grep -E "MemTotal|CmaTotal|CmaFree" /proc/meminfo
ls -lh /path/to/model.rkllm /path/to/model.rknn
```

## Symptom: `invalid RKNN_MAGIC`

Example:

```text
parseRKNN: invalid RKNN_MAGIC
```

Meaning:

The program tried to load something that is not an RKNN file as an RKNN model.

In this project, this happened once because the `imgenc` arguments were in the wrong order.

Correct `imgenc` usage:

```bash
./imgenc <model_path> <image_path> <core_num>
```

Example:

```bash
LD_LIBRARY_PATH=./lib ./imgenc ../models/qwen3-vl_vision_rk3588.rknn demo.jpg 3
```

## Symptom: Demo keeps answering empty prompts

Meaning:

The vendor interactive demo treats EOF as another empty input instead of exiting cleanly.

Current workaround:

Use `timeout`, then validate that the output contains:

```text
rkllm init success
robot:
```

Clean up:

```bash
sudo pkill -x demo 2>/dev/null || true
sudo pkill -x timeout 2>/dev/null || true
```

Better future fix:

Build a non-interactive wrapper that accepts one image and one prompt, prints one answer, then exits.

## Symptom: Large upload silently truncates

Meaning:

Plain `scp` or `sftp` was not reliable enough for multi-hundred-megabyte or multi-gigabyte files.

Fix in project:

Use chunked upload helpers in:

```text
scripts/lib/ssh.py
```

The helper validates remote sizes and resumes already uploaded chunks.

## Symptom: RKLLM toolkit rejects Qwen3-VL

Example:

```text
Not support Qwen3VLForConditionalGeneration
```

Meaning:

The RKLLM toolkit is too old.

For Qwen3-VL-4B, use RKLLM `1.2.3`. RKLLM `1.1.4` was not enough.

## Symptom: W4A16 conversion fails on RK3588

Observed:

```text
target_platform: rk3588 not support quantized_dtype: w4a16
```

Meaning:

RKLLM toolkit `1.2.3` does not support that dtype for this target. Use `w8a8` unless a newer official toolkit explicitly adds support.

## Recovery Notes for Orange Pi Kernel Upgrade

Before the RKNPU upgrade, `/boot` was backed up to:

```text
/home/orangepi/boot-backup-before-rknpu-upgrade-20260630-203252
```

If the board cannot boot after a future kernel change, recovery likely needs serial console, direct SD/eMMC access, or boot media access. Do not overwrite `/boot` again without a recovery path.
