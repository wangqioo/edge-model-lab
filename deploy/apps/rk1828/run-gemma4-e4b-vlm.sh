#!/bin/sh
set -eu

MODEL_DIR="${GEMMA4_MODEL_DIR:-/home/orangepi/lincaigui/gemma4-e4b}"
DEMO_DIR="${GEMMA4_DEMO_DIR:-/home/orangepi/rknn3-model-zoo/install/rk3588_linux_aarch64/rknn_gemma4_demo}"
IMAGE_PATH="${1:-${GEMMA4_IMAGE:-/home/orangepi/rknn3-model-zoo/datasets/COCO/subset/000000419312.jpg}}"
PROMPT="${2:-${GEMMA4_PROMPT:-<image>请用中文简短描述这张图片。}}"
MAX_CONTEXT_LEN="${GEMMA4_MAX_CONTEXT_LEN:-1024}"
MAX_NEW_TOKENS="${GEMMA4_MAX_NEW_TOKENS:-96}"

cd "$DEMO_DIR"
export LD_LIBRARY_PATH="$DEMO_DIR/lib:${LD_LIBRARY_PATH:-}"

exec ./rknn_gemma4_demo \
  "$MODEL_DIR/llm_gemma4-e4b.rknn" \
  "$MODEL_DIR/llm_gemma4-e4b.weight" \
  0xff \
  "$MODEL_DIR/gemma4-e4b.tokenizer.gguf" \
  "$MODEL_DIR/gemma4-e4b.embed.bin" \
  "$MAX_CONTEXT_LEN" \
  "$MAX_NEW_TOKENS" \
  "$MODEL_DIR/gemma4-e4b_per_layer_inputs.embed.bin" \
  "$MODEL_DIR/llm_gemma4-e4b.safetensors" \
  "" \
  "" \
  0 \
  "$MODEL_DIR/vision_gemma4-e4b.rknn" \
  "$MODEL_DIR/vision_gemma4-e4b.weight" \
  0xff \
  "" \
  "$IMAGE_PATH" \
  "$PROMPT"
