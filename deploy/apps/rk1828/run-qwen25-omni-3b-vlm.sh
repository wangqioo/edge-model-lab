#!/bin/sh
set -eu

MODEL_DIR="${QWEN25_OMNI_MODEL_DIR:-/home/orangepi/lincaigui/Qwen2.5-Omni-3B}"
DEMO_DIR="${QWEN25_OMNI_DEMO_DIR:-/home/orangepi/rknn3-model-zoo/install/rk3588_linux_aarch64/rknn_Qwen2_5_Omni_demo}"
IMAGE_PATH="${1:-${QWEN25_OMNI_IMAGE:-$DEMO_DIR/demo.jpg}}"
PROMPT="${2:-${QWEN25_OMNI_PROMPT:-<image>请用中文简短描述这张图片。}}"

cd "$DEMO_DIR"
export LD_LIBRARY_PATH="$DEMO_DIR/lib:${LD_LIBRARY_PATH:-}"

exec ./rknn_qwen2_5_omni_demo \
  "$MODEL_DIR/vision_Qwen2.5-Omni-3B.rknn" \
  "$MODEL_DIR/vision_Qwen2.5-Omni-3B.weight" \
  "" \
  "" \
  "$MODEL_DIR/llm_Qwen2.5-Omni-3B.rknn" \
  "$MODEL_DIR/llm_Qwen2.5-Omni-3B.weight" \
  "$MODEL_DIR/Qwen2.5-Omni-3B.tokenizer.gguf" \
  "$MODEL_DIR/Qwen2.5-Omni-3B.embed.bin" \
  0xff \
  0 \
  0xff \
  "$IMAGE_PATH" \
  "" \
  "$PROMPT"
