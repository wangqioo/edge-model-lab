# Edge Model Lab

Edge Model Lab is the control repository for training, converting, deploying, and validating edge-side AI models on Rockchip boards and RK1828 accelerator hardware.

The project has three execution layers:

- Mac control machine: keeps this repository, documentation, metadata, and `edgectl`.
- Home Linux server: downloads models, runs LoRA/QLoRA fine-tuning, converts models, and packages deployment bundles.
- Rockchip boards and accelerators: run RKNN/RKLLM/RKNN3 workloads on RK3588, RK3576, and RK1828.

Large model files, datasets, and generated artifacts are intentionally not committed to git.

## Current Status

| Target | Role | Current state |
| --- | --- | --- |
| `orange-rk3588` | Orange Pi RK3588, 16GB RAM | Runs `Qwen/Qwen3.5-4B` multimodal inference with RKLLM `1.3.0` and RKNPU `0.9.8` |
| `orange-rk3588` | RK3588 baseline | Also has earlier `Qwen3-VL-4B-Instruct` and Qwen1.5 text baselines |
| RK1828 M.2 accelerator | RK1828 attached to RK3588 host | `Qwen3-VL-4B-Instruct` RKNN3 conversion is complete; PCIe detection works only when RK1828 12V is powered before RK3588 boot; runtime is blocked by missing RK3588 host RKEP kernel support |
| RK1828 M.2 accelerator | Qwen3.5-4B RKNN3 attempt | Vision conversion and LLM ONNX intermediates exist, but LLM RKNN3 build is blocked by Qwen3.5 `linear_attention` graph expansion in `rknn.load_llm` |
| `linaro-rk3576` | RK3576, 8GB RAM | Runs the RK3576 `Qwen3-VL-2B-Instruct` vendor demo and RKNN service tests |
| `lckfb-rk3576` | RK3576, 4GB RAM | Deployment path works, useful for low-memory validation |
| home server | Ubuntu + RTX 4060 Ti 8GB | Good for LoRA/QLoRA, conversion, packaging, and evaluation; not for from-scratch large-model training |

Newest completed RK3588 milestone:

```text
Qwen/Qwen3.5-4B -> RK3588 .rknn + .rkllm -> Orange Pi deployment -> image Q&A smoke passed
```

Deployed RK3588 Qwen3.5 path:

```text
/home/orangepi/edge-model-lab/qwen35-4b-rk3588
```

Detailed record:

```text
docs/experiments/2026-06-30-rk3588-qwen35-4b-conversion.md
```

Newest RK1828 milestone:

```text
Qwen/Qwen3-VL-4B-Instruct -> RKNN3 Toolkit 1.0.4 -> RK1828 vision + LLM artifacts
RK1828 12V first -> RK3588 reboot -> PCIe endpoint 0000:01:00.0 detected
```

RK1828 converted artifacts are on the home server at:

```text
/home/wq/edge-model-lab/models/artifacts/rk1828/qwen3-vl-4b
```

Runtime validation is intentionally not marked complete. The M.2 slot alone is
not treated as a valid powered runtime state for this card. The known-good
bring-up order is RK1828 12V first, wait until RK1828 has fully started and is
physically stable, then boot or reboot the RK3588 host.

Current RK1828 runtime blocker:

```text
RK3588 kernel 6.1.43-rockchip-rk3588 #1.0.8
# CONFIG_PCIE_FUNC_RKEP is not set
rknn3_transfer_proxy can list the RK1828 PCIe endpoint, but rknn3_init fails.
```

The next enablement step is a RK3588 host kernel/runtime package with Rockchip
RKEP PCIe transfer support, not another model conversion attempt.

## RK1828 Safety Rules

These rules are mandatory for RK1828 work. The RK3588 host has been wedged by
unsafe concurrent access to the RK1828 PCIe/RKEP path.

Power sequence:

```text
RK3588 off
RK1828 12V on
wait until RK1828 has fully started and LED/fan state is stable
RK3588 on
```

Runtime access rules:

- Do not hot-plug the RK1828 M.2 card.
- Do not run `rknn3_transfer_proxy`, `pcie_upgrade_tool`, `rknn3_model_test`,
  `rknn3_vlm_demo`, `rknn3_llm_demo`, or `rkllm3-server` concurrently.
- Do not hand-run `pcie_upgrade_tool ... uf`; it has repeatedly made the RK3588
  host unreachable on the current runtime stack.
- Do not use `systemctl start rknn3` or `/bin/rknn3_startup start` for bring-up.
- After any RK3588 recovery, the first command must be a read-only status check.

Use the guarded wrapper for RK1828 runtime operations:

```bash
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py status
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py devices
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py stop-runtime
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py load-driver
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py post-recovery-report
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py start-proxy
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py vision-smoke
```

`status` does not call `rknn3_transfer_proxy`; it is safe as the first check
after the board comes back. `post-recovery-report` is also read-only and is the
preferred evidence bundle after a physical recovery. `devices`, `start-proxy`,
and `vision-smoke` touch the RK1828 runtime path and must remain serialized
through the wrapper. `firmware` is intentionally omitted above: the wrapper now
refuses it unless `--allow-firmware-hang` is passed with local serial/console
recovery ready.

Detailed records:

- [RK1828 Qwen3-VL-4B Runbook](docs/guides/rk1828-qwen3-vl-4b-runbook.md)
- [2026-07-03 RK1828 power and runtime experiment](docs/experiments/2026-07-03-rk1828-12v-power-detection.md)

RK1828 Qwen3.5-4B status:

```text
Qwen/Qwen3.5-4B -> RK1828 vision RKNN3 succeeded
Qwen/Qwen3.5-4B -> LLM ONNX/config/embed/tokenizer succeeded
Qwen/Qwen3.5-4B -> LLM RKNN3 is blocked in load_llm
```

The current blocker is Qwen3.5 `linear_attention`, not missing idle memory. The
probe scripts and notes live in:

```text
scripts/rk1828_qwen35/
docs/experiments/2026-07-02-rk1828-qwen35-4b-rknn3-conversion.md
models/artifacts/rk1828/qwen35-4b/README.md
```

## Repository Layout

```text
benchmarks/          Benchmark plans and results.
deploy/              Systemd units, runtime services, and deployment assets.
docs/                Project design, guides, experiment notes, and runbooks.
inventory/           Device reports and raw audit logs.
models/              Model metadata and asset registry, not model weights.
models/artifacts/    Small artifact metadata in git; large generated files stay ignored.
scripts/             Local control scripts and edgectl implementation.
tests/               Unit tests for local control code.
```

## Start Here

Read these in order:

1. [Project Context](CONTEXT.md)
2. [Project Summary, 2026-06-30](docs/guides/project-summary-2026-06-30.md)
3. [Project Handoff](docs/guides/project-handoff.md)
4. [Device and Model Matrix](docs/guides/device-model-matrix.md)
5. [RK1828 Qwen3-VL-4B Runbook](docs/guides/rk1828-qwen3-vl-4b-runbook.md)
6. [RK3588 Qwen3-VL-4B Runbook](docs/guides/rk3588-qwen3-vl-4b-runbook.md)
7. [Home Server Training Guide](docs/guides/home-server-training.md)
8. [Beginner Deployment Guide](docs/guides/beginner-deployment-guide.md)
9. [Command Reference](docs/guides/command-reference.md)
10. [Troubleshooting](docs/guides/troubleshooting.md)

## Agent Notes

For future agents, this repository has two kinds of truth:

- Git-tracked truth: `README.md`, `CONTEXT.md`, `docs/guides/`, `docs/experiments/`, `models/assets.yaml`, and metadata under `models/artifacts/**/README.md` and `manifest.yaml`.
- Operational truth: large model files and conversion logs on the home server under `/home/wq/edge-model-lab/models/artifacts/`.

Do not infer that RK1828 runtime works from conversion success alone. RK1828
conversion is complete and the powered card now enumerates over PCIe, but
runtime remains blocked until the RK3588 host kernel exposes the RKNN3/RK1828
PCIe transfer driver path.

## Home Server Workflow

The home server is the right place for training-related work:

```text
/home/wq/edge-model-sources/     downloaded base models
/home/wq/edge-datasets/          training and evaluation datasets
/home/wq/edge-training-runs/     LoRA/QLoRA outputs and logs
/home/wq/edge-workspaces/        conversion workspaces
/home/wq/edge-tools/             toolchains and Python environments
/home/wq/edge-logs/              long-running job logs
```

Use it for:

- dataset preparation
- LoRA/QLoRA fine-tuning
- server-side evaluation
- Hugging Face source model downloads
- RKLLM/RKNN conversion
- deployment bundle packaging

For the RTX 4060 Ti 8GB, start with adapter fine-tuning, not full-parameter fine-tuning. A typical path is:

```text
dataset -> LoRA/QLoRA adapter -> merged Hugging Face model -> RKLLM/RKNN conversion -> board smoke test
```

See [Home Server Training Guide](docs/guides/home-server-training.md) for the full process.

## Common Commands

Run from the repository root:

```bash
./scripts/edgectl list
./scripts/edgectl health all
./scripts/edgectl models
./scripts/edgectl models --platform rk3588
./scripts/edgectl models --platform rk3576
./scripts/edgectl models --platform rk1828
```

Smoke deployed RK3588 Qwen3-VL-4B:

```bash
EDGE_ORANGE_RK3588_PASSWORD='...' ./scripts/edgectl rk3588-qwen3-vl-smoke orange-rk3588
```

Deploy or smoke RK3576 Qwen3-VL-2B vendor bundle:

```bash
EDGE_LINARO_RK3576_PASSWORD='...' ./scripts/edgectl llm-deploy linaro-rk3576
EDGE_LCKFB_RK3576_PASSWORD='...' ./scripts/edgectl llm-deploy lckfb-rk3576
```

Run local verification:

```bash
python3 -m compileall scripts tests
python3 -m unittest tests/test_deploy.py tests/test_rknn_service.py
```

## Artifact Rules

Do not commit:

- `.rkllm`
- `.rknn`
- `.onnx`
- `.safetensors`
- datasets with private data
- passwords, access tokens, or local credential files

Commit:

- paths
- commands
- checksums or file sizes
- conversion notes
- board test output summaries
- runbooks

`models/assets.yaml` is the registry for model metadata and local/server/board paths.

## Security

`devices.yaml` intentionally does not store passwords. Use SSH keys where possible.

Temporary local password setup:

```bash
cp devices.local.example.yaml devices.local.yaml
export EDGE_ORANGE_RK3588_PASSWORD='...'
export EDGE_LINARO_RK3576_PASSWORD='...'
export EDGE_LCKFB_RK3576_PASSWORD='...'
```

`devices.local.yaml` is ignored by git.
