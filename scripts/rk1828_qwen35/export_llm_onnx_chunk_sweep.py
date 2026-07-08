#!/usr/bin/env python3
"""Export Qwen3.5 LLM ONNX variants for RK1828 RKNN3 probing."""

import os
import sys
from argparse import Namespace

import torch
from transformers import AutoConfig, Qwen3_5ForConditionalGeneration
from transformers.models.qwen3_5 import modeling_qwen3_5 as qwen35_modeling

MODEL_ZOO_CANDIDATES = [
    os.environ.get("RKNN3_MODEL_ZOO", ""),
    "/home/wq/rknn3-model-zoo",
    "/home/wq/lincaigui/rknn3-model-zoo",
]
MODEL_ZOO = next(path for path in MODEL_ZOO_CANDIDATES if path and os.path.isdir(path))
sys.path.append(MODEL_ZOO)

from py_utils.export_llm_helper import (  # noqa: E402
    causal_llm_to_onnx,
    export_embed_weight,
    export_llm_config,
    export_tokenizer,
)

MODEL_PATH = os.environ.get(
    "QWEN35_MODEL_PATH",
    "/home/wq/edge-model-sources/huggingface/Qwen/Qwen3.5-4B",
)
BASE_OUT = os.environ.get(
    "QWEN35_BASE_OUT",
    "/home/wq/edge-model-lab/models/artifacts/rk1828/qwen35-4b",
)
CHUNK_SIZE = int(os.environ.get("QWEN35_CHUNK_SIZE", "8"))
EXPORT_AUX = os.environ.get("QWEN35_EXPORT_AUX", "0") == "1"
STATIC_SHAPE = os.environ.get("QWEN35_STATIC_SHAPE", "0") == "1"
PROMPT_SIZE = int(os.environ.get("QWEN35_PROMPT_SIZE", "64"))
POSITION_DYNAMIC = os.environ.get("QWEN35_POSITION_DYNAMIC", "0") == "1"


def export_causal_mask(
    config,
    inputs_embeds,
    attention_mask=None,
    cache_position=None,
    *,
    past_key_values=None,
    position_ids=None,
    **kwargs,
):
    """Prefill-only causal mask for Qwen3.5 ONNX tracing."""
    if attention_mask is not None and attention_mask.dim() == 4:
        return attention_mask
    device = inputs_embeds.device
    dtype = inputs_embeds.dtype
    seq_len = torch._shape_as_tensor(inputs_embeds)[1]
    idx = torch.arange(seq_len, device=device)
    future = idx.view(1, -1) > idx.view(-1, 1)
    neg_inf = torch.tensor(torch.finfo(dtype).min, dtype=dtype, device=device)
    zeros = torch.zeros((), dtype=dtype, device=device)
    return torch.where(future, neg_inf, zeros).unsqueeze(0).unsqueeze(0)


qwen35_modeling.create_causal_mask = export_causal_mask


class LanguageModelWithLMHead(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.language_model = model.model.language_model
        self.lm_head = model.lm_head
        self.config = model.config
        self.device = model.device

    def forward(self, input_ids, attention_mask=None, position_ids=None, logits_to_keep=0):
        outputs = self.language_model(
            input_ids=input_ids,
            attention_mask=None,
            position_ids=position_ids,
            use_cache=False,
        )
        hidden_states = outputs[0]
        return self.lm_head(hidden_states.select(1, logits_to_keep).unsqueeze(1))


def safe_update_config(obj, names, value):
    from transformers import PretrainedConfig

    for attr in dir(obj):
        try:
            current = getattr(obj, attr)
        except Exception:
            continue
        if attr in names:
            setattr(obj, attr, value)
        elif isinstance(current, PretrainedConfig):
            safe_update_config(current, names, value)


def static_causal_llm_to_onnx(model, args):
    model.eval()
    in_len = PROMPT_SIZE
    dummy_input = torch.zeros((1, in_len), dtype=torch.long)
    attention_mask = torch.ones((1, in_len), dtype=torch.float)
    position_ids = torch.arange(0, in_len, dtype=torch.long).unsqueeze(0)
    inputs = (dummy_input, attention_mask, position_ids)

    forward_func = model.forward
    while hasattr(forward_func, "__wrapped__"):
        forward_func = forward_func.__wrapped__

    logit_keep_key = None
    for key in ["logits_to_keep", "num_logits_to_keep"]:
        if key in forward_func.__code__.co_varnames:
            logit_keep_key = key
            break
    if logit_keep_key:
        num_logits_to_keep = torch.tensor(-1, dtype=torch.int32).reshape(1)
        insert_nones = [
            None
            for _ in range(forward_func.__code__.co_varnames.index(logit_keep_key) - len(inputs) - 1)
        ]
        inputs = (*inputs, *insert_nones, num_logits_to_keep)

    dynamic_axes = {"position_ids": {1: "sequence"}} if POSITION_DYNAMIC else None
    input_names = ["input_ids", "attention_mask", "position_ids"]
    if logit_keep_key:
        input_names.append("num_logits_to_keep")

    model.float()
    with torch.no_grad():
        torch.onnx.export(
            model,
            inputs,
            args.export_llm_path,
            export_params=True,
            opset_version=19,
            do_constant_folding=True,
            input_names=input_names,
            output_names=["output"],
            dynamic_axes=dynamic_axes,
        )
    print(f"Exported static ONNX to {args.export_llm_path}", flush=True)


def main():
    suffix = f"llm_chunk{CHUNK_SIZE}" + (f"_static{PROMPT_SIZE}" if STATIC_SHAPE else "")
    if STATIC_SHAPE and POSITION_DYNAMIC:
        suffix += "_posdyn"
    out = f"{BASE_OUT}/{suffix}/Qwen3.5-4B-llm"
    os.makedirs(os.path.dirname(out), exist_ok=True)

    config = AutoConfig.from_pretrained(MODEL_PATH, trust_remote_code=True)
    safe_update_config(config, ["use_cache"], False)
    safe_update_config(config, ["_attn_implementation_autoset"], False)
    config._attn_implementation = "eager"
    config.text_config._attn_implementation = "eager"

    print("loading model", MODEL_PATH, "chunk", CHUNK_SIZE, flush=True)
    model = Qwen3_5ForConditionalGeneration.from_pretrained(
        MODEL_PATH,
        config=config,
        torch_dtype=torch.float32,
        low_cpu_mem_usage=True,
        trust_remote_code=True,
    )
    model.eval()

    for layer in model.model.language_model.layers:
        if getattr(layer, "layer_type", None) == "linear_attention":
            original_rule = layer.linear_attn.chunk_gated_delta_rule

            def chunk_rule(*args, _original_rule=original_rule, **kwargs):
                kwargs["chunk_size"] = CHUNK_SIZE
                return _original_rule(*args, **kwargs)

            layer.linear_attn.chunk_gated_delta_rule = chunk_rule

    args = Namespace(export_llm_path=out + ".onnx", hidden_size=config.text_config.hidden_size)
    if STATIC_SHAPE:
        args.dynamic_shape = False

    print("export onnx", args.export_llm_path, flush=True)
    wrapped = LanguageModelWithLMHead(model).eval()
    if STATIC_SHAPE:
        static_causal_llm_to_onnx(wrapped, args)
    else:
        causal_llm_to_onnx(wrapped, args)

    if EXPORT_AUX:
        prompt = "RKLLM"
        chat_context = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "image"}, {"type": "text", "text": prompt}],
                }
            ],
            "add_generation_prompt": True,
        }
        export_llm_config(MODEL_PATH, out + ".config.pkl", chat_context, prompt)
        export_tokenizer(MODEL_PATH, out + ".tokenizer.gguf")
        export_embed_weight(model.model.language_model.embed_tokens.weight, out + ".embed.bin")

    print("DONE", flush=True)


if __name__ == "__main__":
    main()
