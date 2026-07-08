# RK3588 RKLLM Text Smoke on Orange Pi

## Summary

Validated the Orange Pi RK3588 vendor RKLLM text demo on `orange-rk3588`.

The smoke path deploys:

- runtime app: `/opt/edge/apps/rkllm_text_smoke/llm_demo`
- runtime library: `/opt/edge/apps/rkllm_text_smoke/lib/librkllmrt.so`
- model: `/opt/edge/models/Qwen1_5.rkllm`

## Artifacts

- model: `Qwen1_5.rkllm`
  - local size: `795100644`
  - remote size: `759M`
- runtime: `librkllmrt.so`
  - source archive: `RKLLM官网文件/rknn-llm.tar.gz`

## Runtime Evidence

Observed successful initialization:

- `rkllm init start`
- `rkllm-runtime version: 1.1.4`
- `rknpu driver version: 0.9.6`
- `platform: RK3588`
- `rkllm init success`

Observed runtime warning:

- `Your rknpu driver version is too low, please upgrade to 0.9.7.`

Observed generated output from the built-in prompt path. The response was not a clean translation, but the model loaded and generated text, which is enough for the first deployment smoke.

## Interpretation

`orange-rk3588` now has a working RKLLM deployment baseline. It is the best current target for iterative LLM work because it has 16G memory, enough storage, and the RK3588 vendor RKLLM package includes multiple text models.

## Next Actions

- Capture token throughput and memory during generation.
- Try `DeepSeek-R1-Distill-Qwen-1.5B.rkllm` after the Qwen1_5 baseline is stable.
- Upgrade or normalize the RKNPU driver if later RKLLM workloads require `0.9.7`.
