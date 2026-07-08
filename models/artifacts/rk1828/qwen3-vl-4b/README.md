# Qwen3-VL-4B for RK1828

RKNN3 conversion output for `Qwen/Qwen3-VL-4B-Instruct`, target `rk1828`.

The large files in this directory are intentionally ignored by git. Keep them on the home server under:

```text
/home/wq/edge-model-lab/models/artifacts/rk1828/qwen3-vl-4b
```

Runtime bundle:

- `vision/Qwen3-VL-4B-vision-rk1828-prune.rknn`
- `vision/Qwen3-VL-4B-vision-rk1828-prune.weight`
- `llm/Qwen3-VL-4B-llm-rk1828.rknn`
- `llm/Qwen3-VL-4B-llm-rk1828.weight`
- `llm/Qwen3-VL-4B-llm.config.pkl`
- `llm/Qwen3-VL-4B-llm.tokenizer.gguf`
- `llm/Qwen3-VL-4B-llm.embed.bin`

Conversion environment:

- RKNN3 Toolkit: `1.0.4`
- Python env: `/home/wq/edge-tools/rknn3-qwen3vl-py310`
- Source model: `/home/wq/edge-model-sources/huggingface/Qwen/Qwen3-VL-4B-Instruct`
- Model zoo scripts: `/home/wq/lincaigui/rknn3-model-zoo/examples/Qwen3_VL/python`

Status:

- Vision RKNN export succeeded.
- LLM RKNN export succeeded.
- RK1828 PCIe enumeration works with the corrected 12V-first power sequence.
- RKNN3 runtime validation is blocked by the RK3588 host RKEP/runtime stack.
