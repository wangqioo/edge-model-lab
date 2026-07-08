# RK1828 Qwen3.5-4B RKNN3 Conversion Attempt

## Goal

Try converting the already downloaded and RK3588-tested `Qwen/Qwen3.5-4B` model into RK1828 RKNN3 artifacts.

## Source

```text
/home/wq/edge-model-sources/huggingface/Qwen/Qwen3.5-4B
```

The model is multimodal. Its `config.json` reports:

```text
model_type: qwen3_5
architecture: Qwen3_5ForConditionalGeneration
text hidden_size: 2560
vision hidden_size: 1024
```

## Output Root

```text
/home/wq/edge-model-lab/models/artifacts/rk1828/qwen35-4b
```

## Vision Result

Status: succeeded.

The conversion reused the existing Qwen3.5 vision ONNX artifact from the RK3588 work:

```text
/home/wq/edge-workspaces/rkllm-qwen35-4b-rk3588-v130/onnx/qwen3.5_vision.onnx
```

RKNN3 export used:

```text
/home/wq/edge-tools/rknn3-qwen3vl-py310
```

Generated files:

```text
vision/qwen3.5_vision_rk1828.rknn
vision/qwen3.5_vision_rk1828.weight
```

Sizes:

```text
vision/qwen3.5_vision_rk1828.rknn    4,722,496 bytes
vision/qwen3.5_vision_rk1828.weight  197,836,800 bytes
```

The RKNN3 compiler log ended with:

```text
RKNN Compiler All stages completed successfully
```

## LLM Result

Status: ONNX/config/embed/tokenizer exported; RKNN3 LLM build blocked in `load_llm`.

The Qwen3.5-specific environment can load `Qwen3_5ForConditionalGeneration`, but the RKNN3 environment cannot recognize `model_type: qwen3_5`.

Environment split:

```text
/home/wq/edge-tools/qwen35-rkllm130-py310      recognizes Qwen3.5, no RKNN3 toolkit
/home/wq/edge-tools/rknn3-qwen3vl-py310        has RKNN3 toolkit, does not recognize Qwen3.5
```

Attempted approach:

1. Use the Qwen3.5 environment to load the model.
2. Wrap `model.model.language_model` plus `model.lm_head`.
3. Use RKNN3 model-zoo `causal_llm_to_onnx` helper to export an LLM ONNX.

Initial ONNX blocker:

```text
IndexError: tuple index out of range
```

The failure occurs inside:

```text
transformers/masking_utils.py
sdpa_mask()
```

during `torch.onnx.export`. Setting eager attention and omitting the all-ones attention mask did not avoid this path.

Root cause:

During ONNX tracing, Qwen3.5 full-attention mask creation passes a scalar traced `q_length` tensor into Transformers 5.8.0 `sdpa_mask()`. That function treats any tensor `q_length` as the deprecated `cache_position` vector and reads `q_length.shape[0]`, which fails for a 0-d tensor.

Local exporter fix:

- `export_qwen35_llm_onnx.py` monkey-patches Qwen3.5 `create_causal_mask` only inside the export process.
- The replacement mask is a standard additive causal mask for the RKNN3 prefill export case: no KV cache and no padding.
- It does not modify the installed Transformers package.

Successful LLM intermediate outputs:

```text
llm/Qwen3.5-4B-llm.onnx
llm/Qwen3.5-4B-llm.config.pkl
llm/Qwen3.5-4B-llm.embed.bin
llm/Qwen3.5-4B-llm.tokenizer.gguf
```

The ONNX file uses external data files in the same `llm/` directory; the directory was about 20 GiB after export.

Tokenizer note:

- The first GGUF tokenizer export failed because llama.cpp's converter did not recognize the Qwen3.5 BPE pre-tokenizer hash.
- The model still reports `tokenizer_class: Qwen2Tokenizer`.
- A local patched converter mapped hash `1444df51289cfa8063b96f0e62b1125440111bc79a52003ea14b6eac7016fd5f` to `qwen2`, and `logs/05_export_llm_tokenizer_gguf_qwen35_patch.log` records the successful export.

RKNN3 build attempt:

```text
export_qwen35_llm_rknn.py
```

The first attempt used the generic Qwen3 script. It did not pass an explicit sequence range to `load_llm`, so a second dedicated script passed:

```text
seq_lens=[1, 128]
```

Both attempts remained in `rknn.load_llm` and did not reach `rknn.build`. On the second attempt the process reached roughly 29 GiB RSS on the 32 GiB server and used swap; it then exited without a Python traceback. The latest RKNN3 log is:

```text
logs/04_build_llm_rknn3.log
```

Follow-up probes:

- The Qwen3.5 export environment uses CPU PyTorch: `torch 2.6.0+cpu`, `torch.cuda.is_available() == False`.
- The server has an RTX 4060 Ti 8 GiB. A separate fast-path environment was created at `/home/wq/edge-tools/qwen35-fastpath-py310`.
- The fast-path environment has CUDA PyTorch working: `torch 2.6.0+cu124`, CUDA 12.4, GPU visible as `NVIDIA GeForce RTX 4060 Ti`.
- `flash-linear-attention==0.5.1` installs and is detected by Transformers 5.8.0. In `Qwen3_5` import probes, `chunk_gated_delta_rule` and `fused_recurrent_gated_delta_rule` are available.
- `causal-conv1d` is now installed in that environment. The latest official Dao-AILab `1.6.2.post1+cu12torch2.6` wheel was wrong for this host because it imports a new-ABI `torchCheckFail(...std::__cxx11::basic_string...)` symbol while PyTorch `libc10.so` exports the old-ABI `torchCheckFail(...Ss)` symbol. The working wheel is `causal_conv1d-1.5.0.post4+cu124torch2.6cxx11abiFALSE-cp310-cp310-linux_x86_64.whl`.
- After installing that wheel, `probe_fastpath_env.py` reports Qwen3.5 fast-path availability as true for `chunk_gated_delta_rule`, `fused_recurrent_gated_delta_rule`, `causal_conv1d_fn`, and `causal_conv1d_update`.
- `nvidia-cuda-nvcc-cu12==12.4.131` was installed in the fast-path venv, but that wheel provides NVVM/ptxas components rather than a full `nvcc` driver suitable for building `causal-conv1d`.
- A Triton `3.3.0` trial was reverted. It removes the warning from FLA, but `flash-linear-attention==0.5.1` then fails to import `AttrsDescriptor` from Triton. The venv is restored to Triton `3.2.0`, which matches PyTorch `2.6.0`.
- The default fallback ONNX has 212,293 nodes. Most are shape/control-flow expansion from `torch_chunk_gated_delta_rule`, for example `Constant`, `Shape`, `Range`, `Where`, `ScatterND`.
- An experimental `chunk_size=16` exporter reduced the ONNX graph to 70,478 nodes and wrote `llm_chunk16/Qwen3.5-4B-llm.onnx`.
- Even with that smaller graph, a `rknn.load_llm`-only probe filled the 32 GiB server memory and swap and stayed in `load_llm`; it was stopped before `build`.
- Additional CPU fallback sweep:
  - `chunk_size=8` exported successfully to `llm_chunk8/Qwen3.5-4B-llm.onnx` and reduced the graph to 54,822 nodes.
  - `chunk_size=4` exported successfully to `llm_chunk4/Qwen3.5-4B-llm.onnx`, but the graph grew back to 60,686 nodes.
  - `chunk_size=8` with static 64-token input exported successfully to `llm_chunk8_static64/Qwen3.5-4B-llm.onnx`; it has 54,653 nodes and removes `attention_mask` from model inputs, but does not materially reduce graph complexity.
  - `chunk_size=8` is the best fallback chunk size tested so far.
- A `rknn.load_llm`-only probe on the `chunk_size=8` ONNX still filled memory (`30 GiB` used, about `20 GiB` swap used) and did not reach build. It was stopped manually; host memory recovered afterward.
- A `rknn.load_llm`-only probe on the static `chunk_size=8` ONNX also filled memory (`30 GiB` used, about `21 GiB` swap used) and did not reach build. It was stopped manually; host memory recovered afterward.
- On 2026-07-02 21:23 CST, no conversion processes remained. Host memory was about `31 GiB` total, `3.0 GiB` used, and `28 GiB` available; the later apparent memory pressure was from the RKNN3 load itself, not baseline services. Swap was cleaned and restored to `39 GiB` total with `0 B` used via `/swap.img` plus temporary `/swap-rknn32g.img`.
- A minimal FLA-only ONNX probe was run from `/home/wq/edge-tools/probe_fla_onnx_export.py`. After fixing `causal-conv1d`, the FLA forward pass succeeds, but `torch.onnx.export` still fails inside Triton `make_block_ptr`. With Triton `3.3.0`, FLA import fails earlier. Do not attempt a full 4B FLA export until this small probe is fixed.
- A minimal `causal_conv1d_fn` ONNX probe succeeds and writes `/home/wq/edge-tools/probe_causal_conv1d.onnx`, but `causal_conv1d_fn` only runs on CUDA. It cannot be used in the existing CPU export path.
- A Qwen3.5 fp16 CUDA load probe failed on the RTX 4060 Ti 8 GiB. Loading the model to CPU succeeds, but `model.to("cuda")` reaches about `7.52 GiB` GPU memory in use and fails trying to allocate another `20 MiB`. Therefore full-model GPU export on this server is not viable without quantized/offloaded export support.

Temporary probe logs:

```text
logs/06_export_llm_onnx_chunk16.log
logs/07_probe_chunk16_nodes.log
logs/08_probe_chunk16_load_llm.log
logs/09_export_llm_onnx_chunk8.log
logs/10_export_llm_onnx_chunk4.log
logs/11_probe_chunk8_load_llm.log
logs/12_export_llm_onnx_chunk8_static64.log
logs/13_probe_chunk8_static64_load_llm.log
logs/14_optimize_chunk8_static64_onnx.log
logs/15_analyze_chunk8_static64_patterns.log
logs/16_export_llm_onnx_chunk8_static32.log
logs/17_probe_chunk8_static32_load_llm.log
logs/18_export_llm_onnx_chunk8_static16.log
logs/19_probe_chunk8_static16_load_llm.log
logs/20_export_llm_onnx_chunk8_static16_posdyn.log
logs/21_probe_chunk8_static16_posdyn_load_llm.log
logs/22_probe_chunk8_static16_posdyn_seq16_load_llm.log
/home/wq/edge-tools/probe_fastpath_env.log
/home/wq/edge-tools/probe_fla_onnx_export.log
```

## 2026-07-02 Static Prompt and Graph Analysis

The smaller export path was pushed past the earlier `chunk_size=8` and static
64-token probes.

Additional ONNX exports:

| Variant | Prompt/input shape | Position input | Node count | RKNN3 `load_llm` result |
| --- | --- | --- | ---: | --- |
| `llm_chunk8_static32` | `input_ids [1,32]` | `position_ids [1,32]` | 45,533 | Filled 32 GiB host memory plus swap before reaching `build`; stopped manually |
| `llm_chunk8_static16` | `input_ids [1,16]` | `position_ids [1,16]` | 40,973 | Failed quickly: RKNN3 could not replace RoPE because `position_ids` had no dynamic axis |
| `llm_chunk8_static16_posdyn` | `input_ids [1,16]` | `position_ids [1,'sequence']` | 41,071 | Filled host memory during `load_llm`; stopped manually |
| `llm_chunk8_static16_posdyn`, `seq_lens=[1,16]` | `input_ids [1,16]` | `position_ids [1,'sequence']` | 41,071 | Still filled host memory during `load_llm`; stopped manually |

The key RKNN3 error for the fully static 16-token export was:

```text
There are no dynamic axes in position_ids: [1, 16], replace rope branch failed!
```

This means the most aggressive shape clamp only avoids memory pressure by
removing a dynamic axis that RKNN3 needs for RoPE replacement. Adding the
dynamic axis back makes the graph load path fill memory again, even at about
41k nodes. Reducing the `load_llm` sequence range from `[1,128]` to `[1,16]`
does not change that outcome, so the failure is not just caused by the earlier
128-token load range.

Full-graph cleanup was also tested with `onnxoptimizer` and `onnxsim` on
`llm_chunk8_static64`. It is not practical on the current 32 GiB server: loading
and optimizing the 54,653-node external-data model grew to about 29.5 GiB RSS
and about 28 GiB swap before producing useful optimized counts, so the process
was stopped.

`analyze_qwen35_onnx_patterns.py` shows where the graph expansion comes from:

```text
total nodes: 54,653
24 linear_attention layers: about 1,701-1,733 nodes each
8 full_attention layers: about 282 nodes each
other graph nodes: about 10,846
```

Qwen3.5 uses 32 text layers with a repeating pattern of three
`linear_attention` layers followed by one `full_attention` layer. The current
CPU export expands each `linear_attention` fallback implementation into a large
ONNX subgraph. That is the dominant RKNN3 `load_llm` memory problem.

The reproducible scripts are now in the repo:

```text
scripts/rk1828_qwen35/
```

## SDK Support Check

Local RKNN3 SDK documentation for V1.0.4 documents `load_llm` with a small
public surface:

```text
model: .onnx path
config: LLM config .pkl path
seq_lens: sequence length list, default [1,128]
llm_head_dtype
llm_head_quantized_method
```

The documented `llm_config` supports FullAttention, LLM head optimization,
vocab metadata, keep-one-logit, and special mrope handling for `Qwen2.5-VL` and
`Qwen3-VL`. It does not document a Qwen3.5-specific linear-attention path, a
per-layer load mode, or a custom-op escape hatch for `load_llm`.

The local device guide examples cover prebuilt `Qwen3-8B` and
`Qwen3-VL-4B` artifacts for `rkllm3-server`, not Qwen3.5.

An online check on 2026-07-02 found `airockchip/rknn3-toolkit` release V1.0.4
as the latest public GitHub release. The V1.0.4 release notes mention expanded
support for Qwen3-VL, Qwen2.5-Omni, GLM Edge, and SmolVLM, but not Qwen3.5.
The same repo has an open issue from 2026-06-18 asking when `rknn3-toolkit`
will support `qwen3.5`.

Do not confuse this with the separate `airockchip/rknn-llm` RKLLM toolchain:
`rknn-llm` V1.3.0 does list Qwen3.5 support, which matches the successful
RK3588 RKLLM path. RK1828 uses RKNN3/RKLLM3, and the current RKNN3 Toolkit
V1.0.4 public path does not expose a stable Qwen3.5 linear-attention exporter.

References:

```text
https://github.com/airockchip/rknn3-toolkit/releases
https://github.com/airockchip/rknn3-toolkit/issues
https://github.com/airockchip/rknn-llm/releases
```

## Current Conclusion

`Qwen3.5-4B` is not fully converted for RK1828 yet.

What is ready:

- RK1828 vision RKNN3 artifact and external weight.
- Qwen3.5 LLM ONNX/config/embed/tokenizer intermediate files.
- Metadata in `models/artifacts/rk1828/qwen35-4b/manifest.yaml`.
- Asset registry entry `rk1828_qwen35_4b_vision_rknn3`.

What is not ready:

- Qwen3.5 LLM RKNN3 artifact.
- Board-side validation.

Next useful work is no longer another simple prompt-length or chunk-size sweep.
Those knobs have been exhausted on this host. The realistic next paths are:

1. Wait for or obtain a Rockchip Qwen3.5-specific RKNN3 exporter/toolkit path
   that represents Qwen3.5 `linear_attention` directly instead of expanding the
   PyTorch fallback loop.
2. Build a real graph rewrite/custom-op path for the 24 `linear_attention`
   blocks, then prove RKNN3 `load_llm` accepts that representation.
3. Move conversion to a larger-memory machine only if the goal is to test
   whether brute-force `load_llm` can finish; this does not address the likely
   unsupported Qwen3.5 linear-attention semantics.

The current server now has the Python fast-path libraries importable, but the
8 GiB GPU is too small for full-model Qwen3.5 export, FLA Triton kernels are
not directly ONNX-exportable, and the best valid fallback ONNX tested still
overwhelms RKNN3 `load_llm`.
