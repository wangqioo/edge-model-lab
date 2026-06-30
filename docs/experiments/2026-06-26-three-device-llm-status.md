# Three Device LLM Deployment Status

## Summary

Current RKLLM status for the three boards on 2026-06-26:

| Device | Model | Status |
| --- | --- | --- |
| `orange-rk3588` | `Qwen1_5.rkllm` | Deployed and smoke-tested successfully |
| `lckfb-rk3576` | `Qwen3-VL-2B-Instruct` | Deployed; runtime loads; generation hits 4G OOM |
| `linaro-rk3576` | `Qwen3-VL-2B-Instruct` | Deployed and smoke-tested successfully |

## Installed / Target Paths

`orange-rk3588`:

- app: `/opt/edge/apps/rkllm_text_smoke/llm_demo`
- model: `/opt/edge/models/Qwen1_5.rkllm`
- runtime: `/opt/edge/apps/rkllm_text_smoke/lib/librkllmrt.so`

`lckfb-rk3576` and `linaro-rk3576`:

- app: `/opt/edge/apps/rkllm_qwen3_vl_2b/demo`
- image encoder: `/opt/edge/models/qwen3-vl_vision_rk3576.rknn`
- LLM: `/opt/edge/models/qwen3-vl-2b-instruct_w8a8_rk3576.rkllm`
- runtime libs: `/opt/edge/apps/rkllm_qwen3_vl_2b/lib/`

## Notes

- Large model uploads use resumable chunked transfer and remote size validation.
- `orange-rk3588` is the best next board for iterative LLM testing because it has 16G memory and a working text-only RKLLM baseline.
- `lckfb-rk3576` is useful as a low-memory boundary test, not as the main LLM target.
- `linaro-rk3576` confirms that the RK3576 Qwen3-VL bundle can generate on an 8G board without the OOM seen on `lckfb-rk3576`.
