# RKLLM Qwen3-VL Smoke on TaishanPi RK3576

## Summary

Validated the TaishanPi RK3576 vendor `Qwen3-VL-2B-Instruct` Linux demo on `lckfb-rk3576`. The same deployment recipe is being extended to `linaro-rk3576`.

The deployment-side issue was not RKLLM runtime compatibility. The primary blocker was transport integrity:

- direct `scp -O` / `sftp` uploads of the `2.2G` `.rkllm` and `833M` `.rknn` files were truncated
- the board accepted the files reliably only through conservative chunked upload with remote size validation

After replacing the truncated files with complete artifacts:

- RKLLM runtime loaded the `.rkllm` model successfully
- image encoder runtime loaded the `.rknn` model successfully
- the interactive demo progressed into inference
- the process was later `Killed` on the `4G` board during response generation

## Artifacts

- LLM: `qwen3-vl-2b-instruct_w8a8_rk3576.rkllm`
  - local size: `2385677036`
  - remote verified size: `2385677036`
- vision encoder: `qwen3-vl_vision_rk3576.rknn`
  - local size: `873568285`
  - remote verified size: `873568285`

## Runtime evidence

Observed successful initialization:

- `rkllm-runtime version: 1.2.3`
- `platform: RK3576`
- `rkllm-toolkit version: 1.2.3`
- `rkllm init success`
- `main: LLM Model loaded in 10642.20 ms`
- `main: ImgEnc Model loaded in 4738.34 ms`
- `main: ImgEnc Model inference took 2656.28 ms`

Observed failure mode during scripted smoke:

- stderr ended with `Killed`

Kernel OOM evidence confirmed the kill:

- `Out of memory: Killed process ... (demo)`
- `lightdm.service: Failed with result 'oom-kill'`
- `Out of memory: Killed process ... (Xorg)`
- the OOM event happened after successful `rkllm init`, image encoder load, and image encoder inference

## Interpretation

Current conclusion:

1. The vendor RKLLM + RKNN artifacts are loadable on this board.
2. The earlier `rkllm init failed` result was caused by truncated model transfers.
3. The remaining blocker is confirmed global OOM on the `4G` TaishanPi target during answer generation, not deployment plumbing.

## Next actions

- keep chunked upload for large RKLLM/RKNN assets on `lckfb-rk3576`
- keep the resumable chunked upload path and explicit remote size checks in `edgectl llm-deploy`
- capture `dmesg` / kernel OOM evidence immediately after `Killed`
- test reduced runtime settings if the vendor demo supports them
- move the same smoke to a higher-memory RK3576 board if an RKLLM-capable bundle is available there

## linaro-rk3576 Follow-Up

`linaro-rk3576` is the higher-memory RK3576 target. The deployment path now targets it with the same Qwen3-VL files:

- vision encoder: `/opt/edge/models/qwen3-vl_vision_rk3576.rknn`
- LLM: `/opt/edge/models/qwen3-vl-2b-instruct_w8a8_rk3576.rkllm`

Current status on 2026-06-26:

- vision encoder uploaded and verified at `873568285` bytes
- LLM uploaded and installed at `2385677036` bytes
- smoke test completed successfully

Observed successful runtime evidence:

- `rkllm-runtime version: 1.2.3`
- `rknpu driver version: 0.9.7`
- `platform: RK3576`
- `rkllm init success`
- `main: LLM Model loaded in 9466.79 ms`
- `main: ImgEnc Model loaded in 4003.96 ms`
- `main: ImgEnc Model inference took 5233.64 ms`

Observed generated answer for the built-in image prompt:

- `The image portrays a surreal and humorous scene set on the Moon's surface...`

Interpretation:

`linaro-rk3576` confirms that the RK3576 Qwen3-VL-2B-Instruct bundle can load and generate on the 8G RK3576 board. The OOM seen on `lckfb-rk3576` is therefore a low-memory-board constraint, not a general RK3576 deployment failure.
