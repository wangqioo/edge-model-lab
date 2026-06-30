# Home Server Training Guide

This guide explains how to use the home Linux server for model training, fine-tuning, conversion, and evaluation before deploying to the Rockchip boards.

## Server Role

The home server is the project build and training machine.

Known hardware state on 2026-06-30:

```text
host: wq
OS: Ubuntu 24.04
GPU: NVIDIA GeForce RTX 4060 Ti
VRAM: 8188 MiB
RAM: about 31 GiB
disk: about 492 GiB free on /
Python: 3.12.3 system Python
```

Use the server for:

- dataset cleaning and formatting
- LoRA or QLoRA fine-tuning
- small model evaluation
- Hugging Face model downloads
- RKLLM/RKNN conversion
- packaging deploy bundles for RK3588/RK3576 boards

Do not use this server for:

- training a 4B/7B/14B model from scratch
- full-parameter fine-tuning of 4B+ models
- large multi-GPU training assumptions

The RTX 4060 Ti 8GB is useful, but it is still an 8GB VRAM card. Treat it as a single-GPU LoRA/QLoRA machine.

## SSH Access

From the Mac control machine:

```bash
ssh wq@192.168.1.39
```

Use the FRP endpoint only when LAN access is not available. Do not commit FRP credentials or passwords to git.

## Directory Layout

Use these server directories consistently:

```text
/home/wq/edge-model-sources/     downloaded base models
/home/wq/edge-datasets/          training and evaluation datasets
/home/wq/edge-training-runs/     LoRA/QLoRA outputs and logs
/home/wq/edge-workspaces/        conversion workspaces
/home/wq/edge-tools/             toolchains and Python environments
/home/wq/edge-logs/              long-running job logs
```

Large files stay on the server. Git tracks metadata, paths, commands, and results, not model weights.

## What "Training" Means Here

For this project, "training on the home server" normally means fine-tuning an existing model with adapters:

- LoRA: train small low-rank adapter weights while freezing the base model.
- QLoRA: load the base model quantized, then train LoRA adapters to reduce VRAM use.

This is different from training a model from scratch. From-scratch training requires much more compute, much more data, and a different infrastructure plan.

Hugging Face PEFT describes LoRA as freezing the original pretrained weights and training a small set of low-rank adapter parameters. Hugging Face PEFT also documents combining quantization with PEFT, where QLoRA trains LoRA adapters on top of a quantized model.

References:

- <https://huggingface.co/docs/peft/main/conceptual_guides/lora>
- <https://huggingface.co/docs/peft/en/developer_guides/quantization>
- <https://huggingface.co/docs/trl/index>

## Recommended Training Targets

Start with text-only fine-tuning before multimodal fine-tuning.

Good first targets:

- classification prompt tuning
- domain Q&A style adaptation
- command format adaptation
- short instruction-response datasets
- small LoRA adapters for Qwen text models

Be careful with:

- multimodal fine-tuning of Qwen3.5-4B
- long context training
- high-resolution image training
- large batch sizes

For RK3588 deployment, the most practical flow is:

1. Pick a supported base model.
2. Fine-tune with LoRA/QLoRA on the server.
3. Merge adapter weights into the base model if the RKLLM converter needs merged weights.
4. Convert merged model to RKLLM/RKNN.
5. Deploy and test on the board.

## Dataset Format

Keep datasets in JSONL. One record per line.

Text instruction example:

```json
{"messages":[{"role":"system","content":"You are a concise edge device assistant."},{"role":"user","content":"How do I check RKNPU version?"},{"role":"assistant","content":"Run cat /sys/kernel/debug/rknpu/version on the board."}]}
```

Simple prompt-completion example:

```json
{"prompt":"Explain CMA memory for RK3588.","completion":"CMA is a reserved contiguous memory area used by hardware accelerators such as the NPU. Large RKNN/RKLLM workloads may fail if CMA is too small."}
```

Recommended dataset layout:

```text
/home/wq/edge-datasets/<dataset-name>/
  train.jsonl
  eval.jsonl
  README.md
```

Dataset README should record:

- source
- license or permission
- cleaning steps
- number of examples
- intended base model
- intended task

## Environment Setup Pattern

Create one environment per training stack. Do not mix RKLLM conversion packages with training packages.

Example:

```bash
ssh wq@192.168.1.39
mkdir -p /home/wq/edge-tools /home/wq/edge-datasets /home/wq/edge-training-runs
python3 -m venv /home/wq/edge-tools/train-qwen-lora-py312
source /home/wq/edge-tools/train-qwen-lora-py312/bin/activate
python -m pip install --upgrade pip
```

Install training packages only after choosing the exact base model and method. For QLoRA, the usual stack is:

```text
torch
transformers
datasets
accelerate
peft
trl
bitsandbytes
sentencepiece
safetensors
```

Pin versions in a run-specific `requirements.txt` after the first successful run.

## Minimal Run Directory

Every training run should have its own directory:

```text
/home/wq/edge-training-runs/<YYYY-MM-DD>-<model>-<task>/
  config.yaml
  requirements.txt
  train.log
  eval.log
  adapter/
  merged/
  notes.md
```

`config.yaml` should include:

```yaml
base_model: /home/wq/edge-model-sources/huggingface/Qwen/<model-name>
dataset: /home/wq/edge-datasets/<dataset-name>
method: qlora
max_seq_length: 1024
learning_rate: 0.0002
epochs: 1
batch_size_per_device: 1
gradient_accumulation_steps: 8
lora_rank: 8
lora_alpha: 16
target_device: orange-rk3588
target_runtime: rkllm
```

## Training Workflow

Use this workflow for a new fine-tuning task:

1. Create or import dataset under `/home/wq/edge-datasets`.
2. Validate JSONL shape before training.
3. Download or reuse the base model under `/home/wq/edge-model-sources`.
4. Create a new run directory under `/home/wq/edge-training-runs`.
5. Train a LoRA/QLoRA adapter.
6. Run a small eval set on the server.
7. Save adapter and training config.
8. Merge adapter into base model if needed.
9. Convert the merged model with the matching RKLLM release.
10. Deploy to the target board and run a smoke test.
11. Record all paths and output in `docs/experiments/`.

## Resource Defaults for 8GB VRAM

Start conservatively:

```yaml
max_seq_length: 512 or 1024
batch_size_per_device: 1
gradient_accumulation_steps: 8
lora_rank: 8
lora_alpha: 16
gradient_checkpointing: true
load_in_4bit: true
bf16: false
fp16: true
```

If the run OOMs:

1. reduce `max_seq_length`
2. reduce LoRA rank
3. increase gradient accumulation instead of batch size
4. disable image inputs first
5. move to a smaller base model

## Converting After Fine-Tuning

Rockchip deployment usually cannot consume a LoRA adapter by itself. The practical path is:

```text
base model + adapter -> merged Hugging Face model -> RKLLM/RKNN conversion -> board deploy
```

For text-only models:

```text
merged Hugging Face model -> .rkllm
```

For multimodal models:

```text
vision/projector -> .rknn
language model   -> .rkllm
runtime demo     -> board package
```

For Qwen3.5 on RK3588, use RKLLM release `1.3.0` and runtime `1.3.0`.

## Job Logging

Run long jobs with `tmux` or `nohup` and write logs:

```bash
mkdir -p /home/wq/edge-logs
nohup bash train.sh > /home/wq/edge-logs/<run-name>.log 2>&1 &
tail -f /home/wq/edge-logs/<run-name>.log
```

Monitor GPU:

```bash
nvidia-smi
watch -n 2 nvidia-smi
```

Monitor memory and disk:

```bash
free -h
df -h /
```

## Handoff Checklist

Before another person uses the server training flow, make sure this is true:

- SSH access works.
- `/home/wq/edge-model-sources` has the base model or download instructions.
- `/home/wq/edge-datasets/<dataset>` has `train.jsonl`, `eval.jsonl`, and `README.md`.
- `/home/wq/edge-training-runs/<run>` records config, logs, adapter, and eval output.
- The target board and target runtime are written in the run notes.
- No model weights, datasets with private data, tokens, or passwords are committed to git.
