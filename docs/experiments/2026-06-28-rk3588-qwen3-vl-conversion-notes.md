# RK3588 Qwen3-VL Conversion Notes

## Goal

Prepare a path to convert `Qwen3-VL-4B-Instruct` for `orange-rk3588`.

The existing `Qwen3-VL-4B-Instruct` files in the local reference material are RK3576 artifacts:

- `qwen3-vl-4b-instruct_w8a8_rk3576.rkllm`
- `qwen3-vl_vision_rk3576.rknn`

Those files should not be deployed directly on RK3588. RK3588 needs a matching RKLLM and RKNN export.

## Local Source Material

Orange Pi RK3588S package:

`/Users/wq/Documents/ZSPACE/sata11-15850752485/百度网盘下载/香橙派RK3588S/官方工具/RKLLM工具包`

Useful contents:

- `RKLLM官网文件/rknn-llm.tar.gz`
- `第三方工具/Miniforge3-Linux-x86_64.sh`
- `第三方工具/gcc-arm-10.2-2020.11-x86_64-aarch64-none-linux-gnu.tar.xz`
- `转换后的模型/*.rkllm`
- `HuggingFace官网模型/*.7z`

The package includes RKLLM runtime, examples, and a Qwen2-VL multimodal conversion example. It does not include a ready-made Qwen3-VL-4B RK3588 conversion script.

## Reference Example

Extracted from `rknn-llm.tar.gz`:

- `rknn-llm/examples/rkllm_multimodel_demo/README.md`
- `rknn-llm/examples/rkllm_multimodel_demo/export/export_vision.py`
- `rknn-llm/examples/rkllm_multimodel_demo/export/export_vision_rknn.py`
- `rknn-llm/examples/rkllm_multimodel_demo/export/export_rkllm.py`
- `rknn-llm/examples/rkllm_multimodel_demo/data/make_input_embeds_for_quantize.py`

The example targets `Qwen2-VL-2B-Instruct` and uses:

- `rkllm-toolkit==1.1.4`
- `rknn-toolkit2==2.2.1`
- `python==3.8`

Conversion shape:

1. Export Vision + Projector to ONNX.
2. Convert ONNX to RKNN with `target_platform = "rk3588"`.
3. Generate multimodal input embeddings for RKLLM quantization.
4. Export LLM to RKLLM with `target_platform = "rk3588"`, `quantized_dtype = "w8a8"`, and `num_npu_core = 3`.
5. Deploy `demo`, `imgenc`, `librkllmrt.so`, `librknnrt.so`, `.rknn`, and `.rkllm` to Orange Pi.

## Required Adaptation for Qwen3-VL

The Qwen2-VL scripts are not directly reusable without edits.

Expected changes:

- Replace `Qwen2VLForConditionalGeneration` with the correct Qwen3-VL Transformers class or `AutoModelForVision2Seq` equivalent supported by the local Transformers version.
- Update the processor/tokenizer loading path to the Qwen3-VL-4B-Instruct source model.
- Rework the vision export wrapper if Qwen3-VL visual module names, grid handling, patch size, merge size, or projector output differ from Qwen2-VL.
- Regenerate quantization input embeddings using Qwen3-VL chat template and image token handling.
- Export both artifacts for RK3588:
  - `qwen3-vl-4b-instruct_*_rk3588.rkllm`
  - `qwen3-vl_vision_rk3588.rknn`

## Current Blockers

1. The local Orange Pi package includes RKLLM `1.1.4`; that version rejects Qwen3-VL with `Not support Qwen3VLForConditionalGeneration`.
2. Official `rknn-llm` release `1.2.3` includes Qwen3-VL multimodal conversion support and should be used for this model.
3. The conversion host should use Python `3.10`; the control Mac is `darwin/arm64` and cannot run the Linux x86_64 RKLLM wheel.
4. The Qwen3-VL source model and conversion intermediates are large; conversion should run on the home Linux server, not the Mac system disk.

## Hugging Face Source Model

Target model:

- Repo: `Qwen/Qwen3-VL-4B-Instruct`
- Revision checked: `ebb281ec70b05090aa6165b016eac8ec08e71b17`
- Local path: `/Users/wq/Documents/ZSPACE/sata11-15850752485/edge-model-sources/huggingface/Qwen/Qwen3-VL-4B-Instruct`

Expected files include two large weight shards:

- `model-00001-of-00002.safetensors`: `4,967,229,296` bytes
- `model-00002-of-00002.safetensors`: `3,908,490,048` bytes

The first direct `curl -C -` attempt was unstable on long Hugging Face transfers and failed after an SSL read error. The project now uses `edgectl rkllm-download-qwen3-vl-source`, which downloads large files with fixed-size HTTP range chunks and assembles them after all chunks are complete.

## Practical Next Step

Use the official `rknn-llm` `release-v1.2.3` multimodal example, not the older RKLLM `1.1.4` package from the Orange Pi material.

The 1.2.3 README documents Qwen3-VL vision export:

```bash
python export/export_vision.py --path=/path/to/Qwen3-VL --model_name=qwen3-vl --height=448 --width=448
python export/export_vision_rknn.py --path=./onnx/qwen3-vl_vision.onnx --model_name=qwen3-vl --height=448 --width=448
```

The LLM export uses:

```bash
python export/export_rkllm.py --path /path/to/Qwen3-VL --target-platform rk3588 --num_npu_core 3 --quantized_dtype w8a8 --device cpu
```

If the goal is immediate Orange Pi LLM testing instead of conversion research, continue with already converted RK3588 text models such as:

- `DeepSeek-R1-Distill-Qwen-1.5B.rkllm`
- `Qwen.rkllm`
- `InternLM2.rkllm`
- `Phi3.rkllm`
- `chatglm3.rkllm`

## Prepared Tooling

The project now includes a local workspace generator:

```bash
python3 scripts/rkllm_prepare_qwen3_vl_workspace.py /path/to/large-disk/rkllm-qwen3-vl
```

The generated workspace contains:

- RKLLM multimodal conversion example scripts
- RKLLM toolkit Linux x86_64 Python 3.10 wheel, preferably `1.2.3`
- `environment.yml`
- this conversion note as `CONVERSION_NOTES.md`

Important constraints:

- Run the generated workspace on Linux x86_64. The packaged `rkllm_toolkit` wheel is `linux_x86_64`, while the control Mac is `darwin/arm64`.
- Use a disk with enough free space. The control Mac currently has very limited free space and should not be used for downloading and converting Qwen3-VL-4B directly.
- Set `QWEN3_VL_4B_HF_PATH` to the local HuggingFace source model once it exists.

Current local machine checks:

- Control machine architecture: `darwin/arm64`
- Active local Python: `3.13`, not suitable for RKLLM toolkit
- Docker CLI exists, but Docker server is not running in the current session
- `/Users/wq` has only about `12G` free, too small for the source model plus conversion intermediates

Use `edgectl` to prepare the workspace:

```bash
./scripts/edgectl rkllm-prepare-conversion /path/to/large-linux-disk/rkllm-qwen3-vl
```

Use `edgectl` to download or resume the source model:

```bash
./scripts/edgectl rkllm-download-qwen3-vl-source --chunk-mb 32 --workers 4
```

Use `edgectl` to check whether the missing source model is available:

```bash
./scripts/edgectl rkllm-conversion-check
```

## Home Server State on 2026-06-30

Target server:

- SSH: `wq@150.158.146.192:6004`
- LAN IP observed from Mac: `192.168.1.39`
- OS: Ubuntu 24.04.4 LTS, x86_64
- GPU: NVIDIA GeForce RTX 4060 Ti 8GB
- Free root disk during setup: about `608G`

Prepared paths:

- HF source model: `/home/wq/edge-model-sources/huggingface/Qwen/Qwen3-VL-4B-Instruct`
- RKLLM 1.1.4 material: `/home/wq/edge-materials/rk3588-rkllm`
- RKLLM 1.2.3 source release: `/home/wq/edge-tools/rknn-llm-release-v1.2.3`
- RKLLM 1.2.3 wheel: `/home/wq/edge-tools/rknn-llm-release-v1.2.3/rkllm-toolkit/packages/rkllm_toolkit-1.2.3-cp310-cp310-linux_x86_64.whl`
- RKLLM 1.2.3 Python env: `/home/wq/edge-tools/rkllm123-py310`

Completed server checks:

- Both Qwen3-VL safetensor shards were transferred and size-verified:
  - `model-00001-of-00002.safetensors`: `4,967,229,296` bytes
  - `model-00002-of-00002.safetensors`: `3,908,490,048` bytes
- RKLLM 1.1.4 env imported `rkllm.api.RKLLM`, but `load_huggingface` returned `-1` with `Not support Qwen3VLForConditionalGeneration`.
- RKLLM 1.2.3 env imported `rkllm.api.RKLLM` successfully with:
  - `numpy 1.26.4`
  - `protobuf 4.25.4`
  - `pyarrow 21.0.0`
  - `torch 2.6.0+cpu`
  - `transformers 4.55.2`

Interrupted check:

- `RKLLM.load_huggingface` against Qwen3-VL started under 1.2.3 and emitted only a `rope_scaling` warning before the SSH connection was closed by the remote host.
- After that, both FRP SSH `150.158.146.192:6004` and LAN SSH `192.168.1.39:22` accepted TCP but closed or timed out during SSH banner/key exchange.

Recovery commands after SSH returns:

```bash
ssh -p 6004 wq@150.158.146.192 'uptime; free -h; ps -ef | grep -E "qwen3_vl_probe|rkllm|python" | grep -v grep || true'
ssh -p 6004 wq@150.158.146.192 'journalctl -k --since "30 minutes ago" --no-pager | grep -Ei "killed process|out of memory|oom|python" || true'
```

Then rerun the Qwen3-VL load probe under `nohup` so SSH loss does not kill the process.

## Home Server Conversion Run on 2026-06-30

LAN SSH is available at:

```bash
ssh wq@192.168.1.39
```

Extra memory headroom was created before conversion:

- stopped `vllm.service`
- stopped `comfyui.service`
- stopped Docker containers `mineru-gradio` and `docker_ragflow-cpu_1`
- added `/swapfile-rkllm` with `32G`
- total swap during conversion: about `39G`

The first RKLLM `1.2.3` Qwen3-VL load probe succeeded after freeing services:

- log: `/home/wq/edge-tools/qwen3-vl-load-probe-123.log`
- result: `load_huggingface ret 0`
- warning: `rkllm-toolkit only exports Qwen3ForCausalLM of Qwen3VLForConditionalGeneration`

Conversion workspace:

```text
/home/wq/edge-workspaces/rkllm-qwen3-vl-rk3588-v123
```

Generated Qwen3-VL calibration inputs:

- script: `data/make_input_embeds_for_quantize_qwen3.py`
- env: `/home/wq/edge-tools/qwen3vl-vision-py310`
- result: `20` `.npy` input embedding files
- `data/inputs.json`: `164M`

The helper differs from the upstream Qwen2-VL script in these Qwen3-VL-specific ways:

- uses `Qwen3VLForConditionalGeneration`
- uses `model.language_model.embed_tokens(...)`
- uses `next(model.visual.parameters()).dtype`
- handles Qwen3 visual output as a tuple with `[0]`

The RKLLM W8A8 export was started with:

```bash
cd /home/wq/edge-workspaces/rkllm-qwen3-vl-rk3588-v123
/home/wq/edge-tools/rkllm123-py310/bin/python export/export_rkllm.py \
  --path /home/wq/edge-model-sources/huggingface/Qwen/Qwen3-VL-4B-Instruct \
  --target-platform rk3588 \
  --num_npu_core 3 \
  --quantized_dtype w8a8 \
  --device cpu
```

Monitor with:

```bash
cd /home/wq/edge-workspaces/rkllm-qwen3-vl-rk3588-v123
pid=$(cat logs/export-rkllm-qwen3-w8a8.pid)
ps -p "$pid" -o pid,ppid,etime,pcpu,pmem,rss,args
tail -n 120 logs/export-rkllm-qwen3-w8a8.log
ls -lh rkllm
free -h
```

Current observed state:

- `Building model` completed: `547/547`
- calibration dataset loaded: `20 examples`
- optimization reached at least `2/36`
- Python process RSS around `18G`
- swap used around `11G`
- no `.rkllm` artifact yet at that checkpoint

Expected LLM artifact path if export completes:

```text
/home/wq/edge-workspaces/rkllm-qwen3-vl-rk3588-v123/rkllm/qwen3-vl-4b-instruct_w8a8_rk3588.rkllm
```

The vision side still needs to be exported separately to ONNX and converted to RKNN before a full multimodal Orange Pi deployment exists.

## Orange Pi RK3588 Deployment Check on 2026-06-30

Board access used for deployment:

```text
FRP SSH: ssh orangepi@150.158.146.192 -p 6280
LAN SSH: ssh orangepi@192.168.1.52
```

Deployed board path:

```text
/home/orangepi/edge-model-lab/qwen3-vl-rk3588
```

Artifacts on the board:

- `models/qwen3-vl-4b-instruct_w8a8_rk3588.rkllm`
  - size: `4,846,784,612` bytes
  - sha256: `e4c5b2632a43ae5836abb3cde9686c6b20faefc02e378a560d6cbacaa2b362f1`
- `models/qwen3-vl_vision_rk3588.rknn`
  - size: `869,260,061` bytes
  - sha256: `20fd4b06a0b69c22c25fb71a61b4ae5f47d0ab4c7b273198522fc4c0ab220299`
- demo runtime: `demo/demo`, `demo/imgenc`, `demo/lib/librknnrt.so`, `demo/lib/librkllmrt.so`

Vision RKNN board-side validation passed after fixing the standalone `imgenc` probe buffer sizing:

```text
IMGRC:0
main: Model loaded in 1409.92 ms
main: Encoder the image cost 3256.77 ms
img_vec.bin: 7.7M
img_vec.bin sha256: c73f836845f350ddb693f54c52e0983540e31e89a31b23f963c4e7d1ecab422d
```

The upstream standalone `imgenc` probe allocated `model_image_token * model_embed_size` floats, which is only enough for one output tensor. Qwen3-VL vision export has four output tensors shaped `[196, 2560]`, so the probe wrote past the end of its stack buffer and segfaulted. The main multimodal `demo` already allocates `model_image_token * model_embed_size * io_num.n_output`; the workspace helper now patches the probe to use the same sizing.

Full multimodal `demo` currently fails during RKLLM initialization, before vision inference:

```text
W rkllm: Warning: Your rknpu driver version is too low, please upgrade to 0.9.7
I rkllm: rkllm-runtime version: 1.2.3, rknpu driver version: 0.9.6, platform: RK3588
I rkllm: rkllm-toolkit version: 1.2.3, max_context_limit: 4096, npu_core_num: 3, target_platform: RK3588, model_dtype: W8A8
E RKNN: failed to malloc npu memory, size: 4022272000, flags: 0x2
E rkllm: rkllm_init failed
```

Lowering runtime arguments to `max_new_tokens=32`, `max_context_len=512`, and `rknn_core_num=1` still requested the same `4022272000` byte NPU allocation, so this is model-load DMA memory, not prompt/KV-cache size.

Board kernel state:

- kernel: `6.1.43-rockchip-rk3588`
- RKLLM runtime: `1.2.3`
- RKNPU driver reported by RKLLM: `0.9.6`
- RKLLM SDK `1.2.3` document recommends RKNPU driver `0.9.8`
- original boot arg: `cma=128M`

CMA experiments in `/boot/orangepiEnv.txt`:

| `extraargs` value | result after reboot |
| --- | --- |
| `cma=128M` | `CmaTotal: 131072 kB` |
| `cma=2048M` | `CmaTotal: 2097152 kB` |
| `cma=3072M` | `CmaTotal: 3145728 kB` |
| `cma=3584M` | `CmaTotal: 3670016 kB` |
| `cma=3836M` | `CmaTotal: 0 kB` |
| `cma=3840M` | `CmaTotal: 0 kB` |
| `cma=4096M` | `CmaTotal: 0 kB` |
| `cma=5G` | `CmaTotal: 0 kB` |

Current retained boot setting:

```text
extraargs=cma=3584M
```

Backups were left on the board as `/boot/orangepiEnv.txt.bak-qwen3vl-*`.

Conclusion before kernel upgrade:

- Qwen3-VL vision RKNN is deployed and board-runnable.
- Qwen3-VL LLM RKLLM artifact is deployed and hash-verified, but does not load on the current Orange Pi OS because the model needs about `3.75 GiB` of NPU DMA mapping and this kernel only accepts CMA up to `3584M` through the simple boot arg path.
- Full Qwen3-VL multimodal deployment is therefore blocked on board system support, not on file transfer or conversion artifacts.

## RKLLM Low-Memory Export Experiments on 2026-06-30

The first deployed RKLLM was compiled as W8A8, `max_context_limit=4096`, `npu_core_num=3`.
Runtime arguments such as `max_context_len=512` and `rknn_core_num=1` did not change the initial NPU allocation request, so the next experiments rebuilt RKLLM artifacts with smaller compile-time settings.

All artifacts below were exported from:

```text
/home/wq/edge-workspaces/rkllm-qwen3-vl-rk3588-v123
```

and deployed to:

```text
/home/orangepi/edge-model-lab/qwen3-vl-rk3588/models
```

| artifact | size | sha256 | board `model_dtype` | board result |
| --- | ---: | --- | --- | --- |
| `qwen3-vl-4b-instruct_w8a8_ctx1024_rk3588.rkllm` | `4,839,710,660` | `da934e7f8a1e6333ea1eaf5e2ebc1f2447d0675a7da93f30d1e3456a5b6a81f6` | `W8A8`, `npu_core_num: 3` | fails, still requests `4022272000` bytes |
| `qwen3-vl-4b-instruct_w8a8_ctx1024_core1_rk3588.rkllm` | `4,825,683,468` | `671527aa267d66e7e2d6bfbbdc58ced940a38d36209cddc10ebda229165230d2` | `W8A8`, `npu_core_num: 1` | fails, requests `3633315840` bytes |
| `qwen3-vl-4b-instruct_w8a8_g512_ctx1024_core1_rk3588.rkllm` | `4,894,342,084` | `903b233fb55ccd610dfc357811f62e9895171cd0481ebe4d8fa2caa0c3c72f14` | `W8A8_G512`, `npu_core_num: 1` | fails, requests `3633315840` bytes |
| `qwen3-vl-4b-instruct_w8a8_g256_ctx1024_core1_rk3588.rkllm` | `4,971,852,100` | `4472ab0d94cf79d4e2dd01db5af30a6126309a6d5cf86187d5245368f2f12807` | `W8A8_G256`, `npu_core_num: 1` | fails, requests `3633315840` bytes |
| `qwen3-vl-4b-instruct_w8a8_g128_ctx1024_core1_rk3588.rkllm` | `5,126,872,132` | `bd4572f3bfab47fca1c098814867e647bd35c8172fa3aece5e45d70a7d209e4e` | `W8A8_G128`, `npu_core_num: 1` | fails, requests `3633315840` bytes |

Important findings:

- Lowering compile-time `max_context` from `4096` to `1024` changed RKLLM metadata, but did not reduce the model-load NPU allocation.
- Rebuilding with compile-time `num_npu_core=1` changed RKLLM metadata and reduced the allocation request from `4022272000` bytes to `3633315840` bytes.
- W8A8 group-wise quantization (`g512`, `g256`, `g128`) changed file size and metadata, but did not reduce the `3633315840` byte NPU allocation request.
- `w4a16` cannot currently be used for `target_platform=rk3588` with RKLLM toolkit `1.2.3`; build fails with `target_platform: rk3588 not support quantized_dtype: w4a16`.
- `cma=3712M` was also tested and produced `CmaTotal: 0 kB` after reboot, so this board/kernel only accepted up to `cma=3584M` through `/boot/orangepiEnv.txt`.

The best current RKLLM model-load request is therefore:

```text
3633315840 bytes = 3465 MiB
```

The board with `extraargs=cma=3584M` reports:

```text
CmaTotal: 3670016 kB
CmaFree: 3660912 kB
```

Even from a fresh boot, RKLLM/RKNN still fails to allocate the `3633315840` byte handle, likely because the request leaves too little contiguous allocation headroom for the runtime/driver. The remaining blocker is no longer conversion parameter search inside RKLLM W8A8; it is board kernel/driver memory support or choosing a smaller model.

Superseded next routes before the kernel upgrade:

1. Upgrade Orange Pi firmware/kernel or RKNPU driver to the RKLLM 1.2.3 recommended `0.9.8` path, then retry the `core1` model with enough NPU-mappable DMA memory.
2. Build or install a kernel/device-tree configuration that reserves safely more than `3633315840` bytes of contiguous NPU DMA memory.
3. Convert a smaller Qwen3-VL model or another smaller multimodal LLM for immediate full multimodal smoke testing on the current OS.

## Orange Pi RKNPU Upgrade and Qwen3-VL Success on 2026-06-30

The board was upgraded in-place because the RKLLM `1.2.3` runtime needs a newer RKNPU driver than the Orange Pi `1.2.0` Bookworm image shipped.

Pre-upgrade state:

- OS image: `Orange Pi 1.2.0 Bookworm`
- kernel: `6.1.43-rockchip-rk3588 #1.2.0`
- package state:
  - `linux-image-current-rockchip-rk3588 1.2.0`
  - `linux-dtb-current-rockchip-rk3588 1.2.0`
- apt sources: Debian Bookworm only, no Orange Pi kernel repository.
- RKNPU driver reported by RKLLM: `0.9.6`

Upgrade package used:

- source: `https://github.com/cse-repon/orangepi-5b-rknpu-0.9.8-update`
- local file: `linux-image-current-rockchip-rk3588_1.0.8_arm64.deb`
- sha256: `325ecd331e51627c99e96ad8504f71913fd6cc82411f7fcf443697601fe66b0a`
- package contents: `/boot/vmlinuz-6.1.43-rockchip-rk3588`, `/boot/System.map-6.1.43-rockchip-rk3588`, `/boot/config-6.1.43-rockchip-rk3588`, and `/lib/modules/6.1.43-rockchip-rk3588`.
- maintainer script behavior: preinst removes old kernel files on the vfat `/boot`; postinst links `/boot/Image` to the new `vmlinuz`.

Backup before install:

```text
/home/orangepi/boot-backup-before-rknpu-upgrade-20260630-203252
```

Install command:

```bash
sudo dpkg -i /tmp/linux-image-current-rockchip-rk3588_1.0.8_arm64.deb
sudo reboot
```

Post-upgrade state:

```text
Linux orangepi5plus 6.1.43-rockchip-rk3588 #1.0.8 SMP Tue Apr 1 13:54:00 CST 2025 aarch64 GNU/Linux
RKNPU driver: v0.9.8
linux-image-current-rockchip-rk3588 1.0.8
linux-dtb-current-rockchip-rk3588 1.2.0
```

The retained boot CMA setting still applies:

```text
extraargs=cma=3584M
CmaTotal: 3670016 kB
```

Vision RKNN validation after upgrade:

```text
main: Model loaded in 1127.07 ms
main: Encoder the image cost 2531.19 ms
img_vec.bin sha256: c73f836845f350ddb693f54c52e0983540e31e89a31b23f963c4e7d1ecab422d
```

Full Qwen3-VL-4B multimodal validation after upgrade:

```text
I rkllm: rkllm-runtime version: 1.2.3, rknpu driver version: 0.9.8, platform: RK3588
I rkllm: rkllm-toolkit version: 1.2.3, max_context_limit: 4096, npu_core_num: 3, target_platform: RK3588, model_dtype: W8A8
rkllm init success
main: LLM Model loaded in 5110.95 ms
main: ImgEnc Model inference took 2474.95 ms
robot: The image depicts a surreal and humorous scene set on the Moon.
```

Repeatable project smoke:

```bash
EDGE_ORANGE_RK3588_PASSWORD='...' ./scripts/edgectl rk3588-qwen3-vl-smoke orange-rk3588
```

This command returned `0` on 2026-06-30 and verified the deployed original `qwen3-vl-4b-instruct_w8a8_rk3588.rkllm` artifact with `max_context_limit=4096` and `npu_core_num=3`.

Current conclusion:

- Qwen3-VL-4B-Instruct is now deployed and runnable on the Orange Pi RK3588 board.
- The blocking issue was the board kernel/RKNPU driver, not the converted model artifacts.
- The low-memory RKLLM variants remain useful as fallback artifacts, but the default smoke should use the original `ctx4096/core3` model.
- The demo program treats EOF as repeated empty prompts, so automated smoke uses a timeout and requires `rkllm init success` plus `robot:` output rather than a clean demo exit.
