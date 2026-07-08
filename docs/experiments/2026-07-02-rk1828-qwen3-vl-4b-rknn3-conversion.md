# RK1828 Qwen3-VL-4B RKNN3 Conversion

## Goal

Convert `Qwen/Qwen3-VL-4B-Instruct` into RKNN3 artifacts for RK1828 so the RK3588 host can use the RK1828 accelerator once 12V power is connected.

## Target

- Accelerator: RK1828
- Host board: RK3588 Orange Pi 5 Plus
- Toolkit: RKNN3 Toolkit `1.0.4`
- Conversion server: home 4060 Ti server
- Source model: `/home/wq/edge-model-sources/huggingface/Qwen/Qwen3-VL-4B-Instruct`

## Output

Artifacts are stored under:

```text
/home/wq/edge-model-lab/models/artifacts/rk1828/qwen3-vl-4b
```

Runtime files:

- `vision/Qwen3-VL-4B-vision-rk1828-prune.rknn`
- `vision/Qwen3-VL-4B-vision-rk1828-prune.weight`
- `llm/Qwen3-VL-4B-llm-rk1828.rknn`
- `llm/Qwen3-VL-4B-llm-rk1828.weight`
- `llm/Qwen3-VL-4B-llm.config.pkl`
- `llm/Qwen3-VL-4B-llm.tokenizer.gguf`
- `llm/Qwen3-VL-4B-llm.embed.bin`

## Commands

Vision ONNX export:

```bash
/home/wq/edge-tools/rknn3-qwen3vl-py310/bin/python export_vision.py \
  --model_path /home/wq/edge-model-sources/huggingface/Qwen/Qwen3-VL-4B-Instruct \
  --export_vision_path /home/wq/edge-model-lab/models/artifacts/rk1828/qwen3-vl-4b/vision/Qwen3-VL-4B-vision.onnx \
  --img_h 384 --img_w 384
```

Vision RKNN export:

```bash
/home/wq/edge-tools/rknn3-qwen3vl-py310/bin/python export_rknn.py \
  --onnx_path /home/wq/edge-model-lab/models/artifacts/rk1828/qwen3-vl-4b/vision/Qwen3-VL-4B-vision.onnx \
  --rknn_path /home/wq/edge-model-lab/models/artifacts/rk1828/qwen3-vl-4b/vision/Qwen3-VL-4B-vision-rk1828-prune.rknn \
  --platform rk1828 \
  --dataset_path /home/wq/lincaigui/rknn3-model-zoo/datasets/MMBench/vision/datasets.txt \
  --core_num 8
```

LLM RKNN export used:

```bash
/home/wq/edge-tools/rknn3-qwen3vl-py310/bin/python /home/wq/lincaigui/rknn3-model-zoo/examples/Qwen3_VL/python/llm/export_rknn.py \
  --onnx_path /home/wq/edge-model-lab/models/artifacts/rk1828/qwen3-vl-4b/llm/Qwen3-VL-4B-llm.onnx \
  --config /home/wq/edge-model-lab/models/artifacts/rk1828/qwen3-vl-4b/llm/Qwen3-VL-4B-llm.config.pkl \
  --rknn_path /home/wq/edge-model-lab/models/artifacts/rk1828/qwen3-vl-4b/llm/Qwen3-VL-4B-llm-rk1828.rknn \
  --dataset_path /home/wq/edge-model-lab/models/artifacts/rk1828/qwen3-vl-4b/llm/data/llm/dataset.txt \
  --platform rk1828
```

## Result

Both RKNN exports completed successfully. The LLM export log ended with:

```text
RKNN Compiler All stages completed successfully
```

Runtime validation on the physical RK1828 is still pending because the card was not powered by 12V during conversion.

## Notes

- The LLM build needed temporary extra swap during RKNN code generation.
- The model artifacts are large and are intentionally ignored by git. Metadata is tracked in `manifest.yaml` and `models/assets.yaml`.
