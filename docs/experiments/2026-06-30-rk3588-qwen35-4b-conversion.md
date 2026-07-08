# RK3588 Qwen3.5-4B Multimodal Conversion

Date: 2026-06-30

## Goal

Convert `Qwen/Qwen3.5-4B` into Rockchip RK3588 deployable artifacts:

- vision/projector artifact: `.rknn`
- language model artifact: `.rkllm`
- board-side demo bundle for Orange Pi RK3588S

Target board:

- Orange Pi RK3588S, 16GB RAM
- RKNPU driver: `0.9.8`
- LAN SSH: `orangepi@192.168.1.52`
- Existing working baseline: `Qwen3-VL-4B` RKLLM/RKNN smoke test

Build server:

- Ubuntu 24.04 x86_64
- LAN SSH: `wq@192.168.1.39`
- GPU: NVIDIA RTX 4060 Ti 8GB
- RAM: about 31GiB

## Source Model

Hugging Face model:

- repo: `Qwen/Qwen3.5-4B`
- sha: `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a`
- gated: `false`
- pipeline: `image-text-to-text`
- architecture: `Qwen3_5ForConditionalGeneration`
- source size: about `8.7GiB`

Server source directory:

```bash
/home/wq/edge-model-sources/huggingface/Qwen/Qwen3.5-4B
```

Because the server cannot currently reach `huggingface.co` reliably, downloads use:

```bash
https://hf-mirror.com/Qwen/Qwen3.5-4B/resolve/main
```

Download log:

```bash
/home/wq/edge-logs/qwen35-download.log
```

## Toolchain

Rockchip release:

```bash
/home/wq/edge-tools/rknn-llm-release-v1.3.0
```

Reason for using RKLLM `1.3.0`:

- Rockchip `release-v1.3.0` explicitly adds Qwen3.5 support.
- `release-v1.2.3` was enough for Qwen3-VL, but not for this model family.

Python environment:

```bash
/home/wq/edge-tools/qwen35-rkllm130-py310
```

Verified imports:

```text
torch 2.6.0+cpu
torchvision 0.21.0+cpu
transformers 5.8.0
rkllm-toolkit 1.3.0
Qwen3_5ForConditionalGeneration OK
```

`rknn-toolkit2==2.3.2` is required for ONNX to RKNN conversion. Keep it in a separate environment from RKLLM, because its dependency pins conflict with the RKLLM export stack:

```bash
/home/wq/edge-tools/qwen35-rknn232-py310
```

## Workspace

Official Rockchip multimodal example copied to:

```bash
/home/wq/edge-workspaces/rkllm-qwen35-4b-rk3588-v130
```

This workspace contains:

- `export/export_vision.py`
- `export/export_vision_rknn.py`
- `export/export_rkllm.py`
- `data/make_input_embeds_for_quantize.py`
- `deploy/` C++ demo

## Official Conversion Flow

Run commands from:

```bash
cd /home/wq/edge-workspaces/rkllm-qwen35-4b-rk3588-v130
```

Set paths:

```bash
export MODEL_DIR=/home/wq/edge-model-sources/huggingface/Qwen/Qwen3.5-4B
export PY=/home/wq/edge-tools/qwen35-rkllm130-py310/bin/python
```

### 1. Export Vision/Projector ONNX

```bash
$PY export/export_vision.py \
  --path="$MODEL_DIR" \
  --model_name=qwen3.5 \
  --height=448 \
  --width=448 \
  --device=cpu
```

Expected ONNX:

```bash
onnx/qwen3.5_vision.onnx
```

### 2. Convert Vision/Projector ONNX to RKNN

```bash
$PY export/export_vision_rknn.py \
  --path=./onnx/qwen3.5_vision.onnx \
  --model_name=qwen3.5 \
  --target-platform=rk3588 \
  --height=448 \
  --width=448
```

Expected RKNN:

```bash
rknn/qwen3.5_vision_rk3588.rknn
```

### 3. Generate RKLLM Quantization Inputs

```bash
$PY data/make_input_embeds_for_quantize.py \
  --path="$MODEL_DIR" \
  --model_type=qwen3.5
```

Expected calibration metadata:

```bash
data/llm_inputs.json
data/llm_inputs/
```

### 4. Export LLM to RKLLM

```bash
$PY export/export_rkllm.py \
  --path="$MODEL_DIR" \
  --target-platform=rk3588 \
  --num_npu_core=3 \
  --quantized_dtype=w8a8 \
  --device=cpu \
  --savepath=artifacts/qwen3.5-4b_w8a8_rk3588.rkllm
```

### 5. Build Board-Side Demo

```bash
cd deploy
./build-linux.sh
```

The board-side demo must use these multimodal tokens:

```text
<|vision_start|>
<|vision_end|>
<|image_pad|>
```

## Final Status

- RKLLM `1.3.0` release extracted on server.
- Dedicated Python environment created and verified for RKLLM 1.3.0 plus Qwen3.5 transformer class.
- Dedicated RKNN environment created and pinned for `rknn-toolkit2==2.3.2`.
- Conversion workspace created from Rockchip official multimodal demo.
- Model download completed from `hf-mirror.com`.
- Direct `huggingface.co` access from the server timed out, so mirror download was used.
- Local model probe passed:
  - `model_type`: `qwen3_5`
  - architecture: `Qwen3_5ForConditionalGeneration`
  - processor: `Qwen3VLProcessor`
- Vision ONNX export completed:
  - `/home/wq/edge-workspaces/rkllm-qwen35-4b-rk3588-v130/onnx/qwen3.5_vision.onnx`
  - size: about `1.3GB`
- Vision RKNN export produced a file:
  - `/home/wq/edge-workspaces/rkllm-qwen35-4b-rk3588-v130/rknn/qwen3.5_vision_rk3588.rknn`
  - size: about `672MB`
  - caveat: RKNN log contains `REGTASK` bit-width errors and `Unknown op target: 0`; board-side validation still passed on Orange Pi RK3588S.
- LLM calibration inputs completed:
  - `data/llm_inputs.json`
  - `data/inputs.json`
  - 20 calibration samples
- RKLLM W8A8 export completed:
  - `/home/wq/edge-workspaces/rkllm-qwen35-4b-rk3588-v130/rkllm/qwen3.5-4b_w8a8_rk3588.rkllm`
  - size: `5540941884` bytes, about `5.16GiB`
  - log: `/home/wq/edge-workspaces/rkllm-qwen35-4b-rk3588-v130/logs/04_export_rkllm.log`
- Board demo compiled with RKLLM runtime `1.3.0`:
  - `/home/wq/edge-workspaces/rkllm-qwen35-4b-rk3588-v130/deploy/install/demo_Linux_aarch64`
- Deployed to Orange Pi RK3588S:
  - `/home/orangepi/edge-model-lab/qwen35-4b-rk3588`
- Board-side smoke tests passed:
  - Rockchip demo image: loaded `.rkllm`, loaded `.rknn`, generated an image description.
  - User image `/Users/wq/Desktop/111.jpg`: generated a Chinese description of the lake, sunset/sunrise, clouds, light rays, reflection, and distant city skyline.

## Deployed Board Bundle

Orange Pi RK3588S directory:

```bash
/home/orangepi/edge-model-lab/qwen35-4b-rk3588
```

Files:

```text
demo/demo                                           6858224
demo/imgenc                                         6849032
demo/lib/librkllmrt.so                              7617472
demo/lib/librknnrt.so                               7726232
models/qwen3.5-4b_w8a8_rk3588.rkllm                 5540941884
models/qwen3.5_vision_rk3588.rknn                   704579761
run_smoke.sh                                        307
```

Smoke command:

```bash
sshpass -p "$EDGE_ORANGE_RK3588_PASSWORD" ssh orangepi@192.168.1.52 '
cd /home/orangepi/edge-model-lab/qwen35-4b-rk3588
./run_smoke.sh
'
```

Manual image command:

```bash
sshpass -p "$EDGE_ORANGE_RK3588_PASSWORD" ssh orangepi@192.168.1.52 '
cd /home/orangepi/edge-model-lab/qwen35-4b-rk3588/demo
export LD_LIBRARY_PATH="$PWD/lib:$PWD:${LD_LIBRARY_PATH:-}"
printf "1\nexit\n" | ./demo user_111.jpg \
  ../models/qwen3.5_vision_rk3588.rknn \
  ../models/qwen3.5-4b_w8a8_rk3588.rkllm \
  256 4096 3 rk3588 \
  "<|vision_start|>" "<|vision_end|>" "<|image_pad|>"
'
```

Observed board load timings:

```text
LLM model load: about 17-18.5s
Image encoder load: about 1.9-2.1s
Image encoder inference: about 2.2-2.3s
Runtime: rkllm-runtime 1.3.0
RKNPU driver: 0.9.8
Vision input: 448x448
Vision tokens: 196
Embedding dim: 2560
```

## Watch Commands

Download:

```bash
ssh wq@192.168.1.39 'tail -f /home/wq/edge-logs/qwen35-download.log'
```

Workspace size:

```bash
ssh wq@192.168.1.39 'du -sh /home/wq/edge-model-sources/huggingface/Qwen/Qwen3.5-4B'
```

Running conversion jobs:

```bash
ssh wq@192.168.1.39 'ps -eo pid,etime,args | grep -E "qwen35|Qwen3.5|export_vision|export_rkllm" | grep -v grep'
```

## Issues Observed

### Server Cannot Reach Hugging Face Directly

The server repeatedly timed out on:

```bash
https://huggingface.co/Qwen/Qwen3.5-4B
```

The working endpoint was:

```bash
https://hf-mirror.com/Qwen/Qwen3.5-4B/resolve/main
```

### RKNN Toolkit Dependency Pinning

`rknn-toolkit2==2.3.2` installed `onnx==1.22.0` by default, but RKNN toolkit expects `onnx.mapping`, which is absent in newer ONNX releases. The fix was:

```bash
/home/wq/edge-tools/qwen35-rknn232-py310/bin/python -m pip install 'onnx==1.16.1'
```

`rknn-toolkit2` also needs `pkg_resources`, so the isolated RKNN environment pins setuptools below the removal boundary:

```bash
/home/wq/edge-tools/qwen35-rknn232-py310/bin/python -m pip install 'setuptools<82'
```

### Vision RKNN Compiler Errors

The 448x448 vision RKNN export wrote a `.rknn` file but logged errors like:

```text
REGTASK: The bit width of field value exceeds the limit
Unkown op target: 0
```

Despite these compiler errors, the generated `.rknn` loaded and ran on the Orange Pi RK3588S. Keep this warning in the record because a future runtime, driver, or model resolution change may expose it again.

If the vision model fails later, the next mitigation is to export a lower-resolution vision model, for example `336x336`.

### RKLLM Export Save Path

`export/export_rkllm.py` accepts `--savepath`, but the official script computes its own output path from the model directory name and target platform. The actual output was:

```bash
./rkllm/qwen3.5-4b_w8a8_rk3588.rkllm
```

Do not rely on the passed `--savepath` unless the script is patched.

### Runtime Symlink Mismatch

The demo `CMakeLists.txt` expects RKLLM runtime at:

```bash
../../../rkllm-runtime
```

From the copied workspace this resolved to:

```bash
/home/wq/rkllm-runtime
```

That symlink initially pointed to RKLLM `1.2.3`, which caused compile errors against the old `rkllm.h` API. The fix was:

```bash
ln -sfn /home/wq/edge-tools/rknn-llm-release-v1.3.0/rkllm-runtime /home/wq/rkllm-runtime
```

After this, `deploy/build-linux.sh` compiled and installed the board demo successfully.
