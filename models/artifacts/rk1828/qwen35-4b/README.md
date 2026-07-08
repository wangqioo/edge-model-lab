# Qwen3.5-4B for RK1828

Partial RKNN3 conversion output for `Qwen/Qwen3.5-4B`, target `rk1828`.

Status as of 2026-07-02:

- Vision RKNN3 conversion succeeded.
- LLM ONNX/config/embed/tokenizer export succeeded after an exporter-local Qwen3.5 mask patch.
- LLM RKNN3 conversion is blocked in `rknn.load_llm`; default, chunked, and static-prompt ONNX variants either consume server memory plus swap before reaching `build` or fail because RKNN3 needs a dynamic `position_ids` axis for RoPE replacement.
- RK1828 PCIe enumeration works with the corrected 12V-first power sequence; RKNN3 runtime validation is blocked by the RK3588 host RKEP/runtime stack.

The large files in this directory are intentionally ignored by git. Keep them on the home server under:

```text
/home/wq/edge-model-lab/models/artifacts/rk1828/qwen35-4b
```

Ready runtime files:

- `vision/qwen3.5_vision_rk1828.rknn`
- `vision/qwen3.5_vision_rk1828.weight`

Ready LLM intermediate files:

- `llm/Qwen3.5-4B-llm.onnx`
- `llm/Qwen3.5-4B-llm.config.pkl`
- `llm/Qwen3.5-4B-llm.tokenizer.gguf`
- `llm/Qwen3.5-4B-llm.embed.bin`

Attempted but not completed:

- `llm/Qwen3.5-4B-llm-rk1828.rknn`
- `llm/Qwen3.5-4B-llm-rk1828.weight`

Conversion environments:

- Vision source ONNX: `/home/wq/edge-workspaces/rkllm-qwen35-4b-rk3588-v130/onnx/qwen3.5_vision.onnx`
- Vision RKNN3 conversion: `/home/wq/edge-tools/rknn3-qwen3vl-py310`
- Qwen3.5 model source and LLM ONNX export: `/home/wq/edge-tools/qwen35-rkllm130-py310`
- LLM RKNN3 build attempt: `/home/wq/edge-tools/rknn3-qwen3vl-py310`
- Source model: `/home/wq/edge-model-sources/huggingface/Qwen/Qwen3.5-4B`

Reproduction scripts on the server:

- `export_qwen35_llm_onnx.py`
- `export_qwen35_llm_rknn.py`

Relevant logs:

- `logs/02_export_llm_onnx.log`: successful ONNX export after mask patch.
- `logs/03_export_llm_tokenizer_gguf.log`: original tokenizer GGUF failure, missing Qwen3.5 pre-tokenizer hash.
- `logs/05_export_llm_tokenizer_gguf_qwen35_patch.log`: successful tokenizer GGUF export with a local hash mapping to `qwen2`.
- `logs/04_build_llm_rknn3.log`: RKNN3 `load_llm` attempt that did not reach `build`.
- `logs/06_export_llm_onnx_chunk16.log`: experimental smaller ONNX export with `GatedDeltaNet` chunk size forced to 16.
- `logs/07_probe_chunk16_nodes.log`: node-count comparison, default 212,293 nodes versus chunk16 70,478 nodes.
- `logs/08_probe_chunk16_load_llm.log`: `rknn.load_llm`-only probe for the chunk16 ONNX; it also filled memory/swap and was stopped.
- `logs/15_analyze_chunk8_static64_patterns.log`: ONNX layer analysis showing the graph is dominated by Qwen3.5 `linear_attention` expansion.
- `logs/17_probe_chunk8_static32_load_llm.log`: static 32-token probe; still filled memory.
- `logs/19_probe_chunk8_static16_load_llm.log`: static 16-token probe; failed because static `position_ids` has no dynamic axis for RKNN3 RoPE replacement.
- `logs/21_probe_chunk8_static16_posdyn_load_llm.log`: static 16-token input with dynamic `position_ids`; filled memory again.
- `logs/22_probe_chunk8_static16_posdyn_seq16_load_llm.log`: same ONNX with `seq_lens=[1,16]`; still filled memory.

The main blocker is Qwen3.5 `linear_attention`: the current CPU PyTorch export environment lacks `flash-linear-attention` and `causal-conv1d`, so Transformers traces the pure torch fallback into a very large ONNX graph.

2026-07-02 fast-path follow-up:

- `/home/wq/edge-tools/qwen35-fastpath-py310` now has CUDA PyTorch `2.6.0+cu124` working on the server RTX 4060 Ti.
- `flash-linear-attention==0.5.1` is installed and Transformers detects the Qwen3.5 gated-delta kernels.
- `causal-conv1d` is installed with the working Dao-AILab wheel `1.5.0.post4+cu124torch2.6cxx11abiFALSE`. The newer `1.6.2.post1+cu12torch2.6` wheel has a PyTorch C++ ABI symbol mismatch on this host.
- A minimal FLA-only ONNX probe still fails during `torch.onnx.export`: FLA forward succeeds, but tracing fails inside Triton `make_block_ptr`. Triton `3.3.0` breaks FLA import, so the fast-path venv has been restored to Triton `3.2.0`.
- A minimal `causal_conv1d_fn` ONNX probe succeeds, but that kernel is CUDA-only. Full Qwen3.5 fp16 GPU export is not viable on the server's 8 GiB RTX 4060 Ti; `model.to("cuda")` OOMs at about 7.52 GiB used.
- CPU fallback graph compression was pushed further. `chunk_size=8` is best so far at 54,822 nodes; `chunk_size=4` grows back to 60,686 nodes. A static 64-token `chunk_size=8` export has 54,653 nodes but still fills memory during `rknn.load_llm`.
- Static prompt probing did not solve the blocker. Static 32-token export has 45,533 nodes and still fills memory in `load_llm`. Static 16-token export has 40,973 nodes but fails because RKNN3 cannot replace RoPE without a dynamic axis in `position_ids`. Adding that dynamic axis back gives 41,071 nodes and fills memory again.
- The `llm_chunk8_static16_posdyn` probe was also run with `seq_lens=[1,16]` instead of `[1,128]`; it still filled memory. The blocker is therefore not just an oversized sequence-length range passed to `load_llm`.
- ONNX graph analysis shows 24 Qwen3.5 `linear_attention` layers at about 1,701-1,733 nodes each, versus 8 `full_attention` layers at about 282 nodes each. The blocker is therefore Qwen3.5 linear-attention fallback expansion, not idle host memory.
- Full-graph `onnxoptimizer`/`onnxsim` cleanup is not practical on the current 32 GiB server; the optimizer process reached about 29.5 GiB RSS plus heavy swap before producing a useful result.
- Memory was cleaned after the failed probes: swap was restored to 39 GiB with 0 B used. The previous failure is still attributed to RKNN3 `load_llm` graph expansion, not idle memory pressure.

Repo scripts:

- `scripts/rk1828_qwen35/export_llm_onnx_chunk_sweep.py`
- `scripts/rk1828_qwen35/probe_load_llm.py`
- `scripts/rk1828_qwen35/analyze_onnx_patterns.py`
- `scripts/rk1828_qwen35/optimize_static_onnx.py`

Current conclusion: do not keep spending time on simple `chunk_size` or prompt
length sweeps. The next viable path needs Rockchip Qwen3.5-specific RKNN3
support or a deliberate rewrite/custom-op representation for the 24
`linear_attention` blocks.
