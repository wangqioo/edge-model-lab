from __future__ import annotations

import os
import re
import shutil
import tarfile
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from subprocess import CalledProcessError, run


RK3588_RKLLM_ROOT = Path(
    os.environ.get(
        "RK3588_RKLLM_ROOT",
        "/Users/wq/Documents/ZSPACE/sata11-15850752485/百度网盘下载/香橙派RK3588S/官方工具/RKLLM工具包",
    )
)
RKNN_LLM_TAR = RK3588_RKLLM_ROOT / "RKLLM官网文件/rknn-llm.tar.gz"
MINIFORGE = RK3588_RKLLM_ROOT / "第三方工具/Miniforge3-Linux-x86_64.sh"
GCC_TOOLCHAIN = RK3588_RKLLM_ROOT / "第三方工具/gcc-arm-10.2-2020.11-x86_64-aarch64-none-linux-gnu.tar.xz"
RKNN_LLM_123_ROOT = Path(
    os.environ.get(
        "RKNN_LLM_123_ROOT",
        "/home/wq/edge-tools/rknn-llm-release-v1.2.3",
    )
)
RKNN_LLM_123_TAR = Path(
    os.environ.get(
        "RKNN_LLM_123_TAR",
        "/home/wq/edge-tools/rknn-llm-release-v1.2.3.tar.gz",
    )
)
QWEN3_VL_4B_RK3576_ROOT = Path(
    os.environ.get(
        "QWEN3_VL_4B_RK3576_ROOT",
        "/Users/wq/Documents/ZSPACE/sata11-15850752485/百度网盘下载/立创·泰山派RK3576开发板资料/8.【立创·泰山派3】Ai应用/Qwen3-VL-4B-Instruct/2025-12-31",
    )
)
QWEN3_VL_4B_RK3576_LLM = QWEN3_VL_4B_RK3576_ROOT / "qwen3-vl-4b-instruct_w8a8_rk3576.rkllm"
QWEN3_VL_4B_RK3576_VISION = QWEN3_VL_4B_RK3576_ROOT / "qwen3-vl_vision_rk3576.rknn"
QWEN3_VL_4B_HF_REPO = "Qwen/Qwen3-VL-4B-Instruct"
QWEN3_VL_4B_HF_REVISION = "ebb281ec70b05090aa6165b016eac8ec08e71b17"
DEFAULT_QWEN3_VL_4B_HF_PATH = Path(
    os.environ.get(
        "QWEN3_VL_4B_HF_PATH",
        "/Users/wq/Documents/ZSPACE/sata11-15850752485/edge-model-sources/huggingface/Qwen/Qwen3-VL-4B-Instruct",
    )
)
QWEN3_VL_4B_HF_FILES = (
    ".gitattributes",
    "README.md",
    "chat_template.json",
    "config.json",
    "generation_config.json",
    "merges.txt",
    "model-00001-of-00002.safetensors",
    "model-00002-of-00002.safetensors",
    "model.safetensors.index.json",
    "preprocessor_config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "video_preprocessor_config.json",
    "vocab.json",
)
QWEN3_VL_4B_HF_FILE_SIZES = {
    ".gitattributes": 1519,
    "README.md": 7133,
    "chat_template.json": 5502,
    "config.json": 1505,
    "generation_config.json": 269,
    "merges.txt": 1671839,
    "model-00001-of-00002.safetensors": 4967229296,
    "model-00002-of-00002.safetensors": 3908490048,
    "model.safetensors.index.json": 64742,
    "preprocessor_config.json": 390,
    "tokenizer.json": 7032403,
    "tokenizer_config.json": 10868,
    "video_preprocessor_config.json": 385,
    "vocab.json": 2776833,
}
CHUNKED_DOWNLOAD_THRESHOLD_BYTES = 256 * 1024 * 1024
DEFAULT_CHUNK_SIZE_BYTES = 64 * 1024 * 1024
DEFAULT_DOWNLOAD_WORKERS = 4

REQUIRED_LEGACY_MULTIMODAL_EXAMPLE_FILES = (
    "rknn-llm/examples/rkllm_multimodel_demo/README.md",
    "rknn-llm/examples/rkllm_multimodel_demo/export/export_vision.py",
    "rknn-llm/examples/rkllm_multimodel_demo/export/export_vision_rknn.py",
    "rknn-llm/examples/rkllm_multimodel_demo/export/export_rkllm.py",
    "rknn-llm/examples/rkllm_multimodel_demo/data/make_input_embeds_for_quantize.py",
)
REQUIRED_RKLLM_123_EXAMPLE_FILES = (
    "examples/multimodal_model_demo/README.md",
    "examples/multimodal_model_demo/export/export_vision.py",
    "examples/multimodal_model_demo/export/export_vision_rknn.py",
    "examples/multimodal_model_demo/export/export_rkllm.py",
    "examples/multimodal_model_demo/data/make_input_embeds_for_quantize.py",
    "rkllm-toolkit/packages/rkllm_toolkit-1.2.3-cp310-cp310-linux_x86_64.whl",
)
LEGACY_RKLLM_WHEEL = "rknn-llm/rkllm-toolkit/packages/rkllm_toolkit-1.1.4-cp310-cp310-linux_x86_64.whl"
RKLLM_123_WHEEL = "rkllm-toolkit/packages/rkllm_toolkit-1.2.3-cp310-cp310-linux_x86_64.whl"
LEGACY_WORKSPACE_MEMBERS = (
    "rknn-llm/README.md",
    "rknn-llm/examples/rkllm_multimodel_demo",
    LEGACY_RKLLM_WHEEL,
)

QWEN3_VL_INPUT_HELPER = """\
import argparse
import json
import os
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from tqdm import tqdm
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

parser = argparse.ArgumentParser()
parser.add_argument("--path", required=True, help="Qwen3-VL model path")
parser.add_argument("--limit", type=int, default=20, help="maximum calibration records")
args = parser.parse_args()

model = Qwen3VLForConditionalGeneration.from_pretrained(
    args.path,
    torch_dtype="auto",
    device_map="cpu",
    low_cpu_mem_usage=True,
    _attn_implementation="eager",
    trust_remote_code=True,
).eval()
processor = AutoProcessor.from_pretrained(args.path, trust_remote_code=True)

datasets = json.load(open("data/datasets.json", "r", encoding="utf-8"))[: args.limit]
os.makedirs("data/inputs_embeds", exist_ok=True)

for data in tqdm(datasets):
    image_name = Path(data["image"]).stem
    imgp = os.path.join(data["image_path"], data["image"])
    image = Image.open(imgp).convert("RGB")
    conversation = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": data["input"]},
            ],
        }
    ]
    text_prompt = processor.apply_chat_template(conversation, add_generation_prompt=True)
    inputs = processor(text=[text_prompt], images=[image], padding=True, return_tensors="pt")
    inputs = inputs.to(model.device)
    inputs_embeds = model.language_model.embed_tokens(inputs["input_ids"])
    pixel_values = inputs["pixel_values"].type(next(model.visual.parameters()).dtype)
    image_mask = inputs["input_ids"] == model.config.image_token_id
    image_embeds = model.visual(pixel_values, grid_thw=inputs["image_grid_thw"])[0].to(inputs_embeds.device)
    inputs_embeds[image_mask] = image_embeds
    print("inputs_embeds", image_name, tuple(inputs_embeds.shape), flush=True)
    np.save(f"data/inputs_embeds/{image_name}.npy", inputs_embeds.to(dtype=torch.float16).cpu().detach().numpy())

with open("data/inputs.json", "w", encoding="utf-8") as json_file:
    json_file.write("[\\n")
    first = True
    for data in tqdm(datasets):
        input_embed = np.load(os.path.join("data/inputs_embeds", Path(data["image"]).stem + ".npy"))
        input_dict = {"input_embed": input_embed.tolist(), "target": data["target"]}
        if not first:
            json_file.write(",\\n")
        else:
            first = False
        json.dump(input_dict, json_file, ensure_ascii=False)
    json_file.write("\\n]")
print("Done", flush=True)
"""

QWEN3_VL_RKLLM_CONTEXT_EXPORT = """\
import argparse
import os

from rkllm.api import RKLLM

parser = argparse.ArgumentParser()
parser.add_argument("--path", required=True)
parser.add_argument("--target-platform", default="rk3588")
parser.add_argument("--num_npu_core", type=int, default=3)
parser.add_argument("--quantized_dtype", default="w8a8")
parser.add_argument("--device", default="cpu")
parser.add_argument("--max_context", type=int, default=1024)
parser.add_argument("--savepath", required=True)
args = parser.parse_args()

os.makedirs(os.path.dirname(args.savepath), exist_ok=True)

llm = RKLLM()
print(f"load_huggingface path={args.path} device={args.device}", flush=True)
ret = llm.load_huggingface(model=args.path, device=args.device)
print(f"load_huggingface ret={ret}", flush=True)
if ret != 0:
    raise SystemExit(ret)

print(
    "build "
    f"dtype={args.quantized_dtype} target={args.target_platform} cores={args.num_npu_core} "
    f"max_context={args.max_context}",
    flush=True,
)
ret = llm.build(
    do_quantization=True,
    optimization_level=1,
    quantized_dtype=args.quantized_dtype,
    quantized_algorithm="normal",
    target_platform=args.target_platform,
    num_npu_core=args.num_npu_core,
    extra_qparams=None,
    dataset="data/inputs.json",
    hybrid_rate=0,
    max_context=args.max_context,
)
print(f"build ret={ret}", flush=True)
if ret != 0:
    raise SystemExit(ret)

print(f"export {args.savepath}", flush=True)
ret = llm.export_rkllm(args.savepath)
print(f"export ret={ret}", flush=True)
raise SystemExit(ret)
"""

QWEN3_VL_EXPORT_HELPER = """\
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
WORKSPACE=${WORKSPACE:-"$SCRIPT_DIR"}
MODEL=${MODEL:-/home/wq/edge-model-sources/huggingface/Qwen/Qwen3-VL-4B-Instruct}
VISION_PY=${VISION_PY:-/home/wq/edge-tools/qwen3vl-vision-py310/bin/python}
RKLLM_PY=${RKLLM_PY:-/home/wq/edge-tools/rkllm123-py310/bin/python}
LIMIT=${LIMIT:-20}
MAX_CONTEXT=${MAX_CONTEXT:-1024}
QUANTIZED_DTYPE=${QUANTIZED_DTYPE:-w8a8}
TARGET_PLATFORM=${TARGET_PLATFORM:-rk3588}
NUM_NPU_CORE=${NUM_NPU_CORE:-3}
DEVICE=${DEVICE:-cpu}
SAVE_PATH=${SAVE_PATH:-"rkllm/qwen3-vl-4b-instruct_${QUANTIZED_DTYPE}_ctx${MAX_CONTEXT}_${TARGET_PLATFORM}.rkllm"}

cd "$WORKSPACE"
mkdir -p logs rkllm

if [ ! -s data/inputs.json ]; then
  rm -rf data/inputs_embeds data/inputs.json
  "$VISION_PY" data/make_input_embeds_for_quantize_qwen3.py --path "$MODEL" --limit "$LIMIT"
fi

exec "$RKLLM_PY" export/export_rkllm_qwen3_context.py \\
  --path "$MODEL" \\
  --target-platform "$TARGET_PLATFORM" \\
  --num_npu_core "$NUM_NPU_CORE" \\
  --quantized_dtype "$QUANTIZED_DTYPE" \\
  --device "$DEVICE" \\
  --max_context "$MAX_CONTEXT" \\
  --savepath "$SAVE_PATH"
"""


@dataclass(frozen=True)
class ConversionCheck:
    name: str
    status: str
    detail: str


def _path_check(name: str, path: Path) -> ConversionCheck:
    return ConversionCheck(name, "ok" if path.exists() else "missing", str(path))


def _tar_member_check(tar_path: Path, members: tuple[str, ...]) -> list[ConversionCheck]:
    if not tar_path.exists():
        return [ConversionCheck("Qwen2-VL multimodal example", "missing", f"missing tar: {tar_path}")]
    try:
        with tarfile.open(tar_path, "r:gz") as archive:
            names = set(archive.getnames())
    except tarfile.TarError as error:
        return [ConversionCheck("Qwen2-VL multimodal example", "error", str(error))]
    return [
        ConversionCheck(f"example:{Path(member).name}", "ok" if member in names else "missing", member)
        for member in members
    ]


def _directory_member_check(root: Path, members: tuple[str, ...], prefix: str) -> list[ConversionCheck]:
    if not root.exists():
        return [ConversionCheck(prefix, "missing", str(root))]
    return [
        ConversionCheck(f"{prefix}:{Path(member).name}", "ok" if (root / member).exists() else "missing", str(root / member))
        for member in members
    ]


def collect_rk3588_qwen3_vl_conversion_checks() -> list[ConversionCheck]:
    source_model = Path(os.environ.get("QWEN3_VL_4B_HF_PATH", str(DEFAULT_QWEN3_VL_4B_HF_PATH)))
    missing_source_files = [
        name
        for name in QWEN3_VL_4B_HF_FILES
        if not (source_model / name).exists()
        or (name in QWEN3_VL_4B_HF_FILE_SIZES and (source_model / name).stat().st_size != QWEN3_VL_4B_HF_FILE_SIZES[name])
    ]
    checks = [
        _path_check("RKLLM package root", RK3588_RKLLM_ROOT),
        _path_check("rknn-llm archive", RKNN_LLM_TAR),
        _path_check("Miniforge installer", MINIFORGE),
        _path_check("aarch64 GCC toolchain", GCC_TOOLCHAIN),
        _path_check("RKLLM 1.2.3 release root", RKNN_LLM_123_ROOT),
        ConversionCheck(
            "Qwen3-VL-4B HuggingFace source",
            "ok" if source_model.exists() and not missing_source_files else "missing",
            f"{source_model} missing files: {', '.join(missing_source_files)}"
            if missing_source_files
            else str(source_model),
        ),
        _path_check("reference RK3576 Qwen3-VL-4B LLM", QWEN3_VL_4B_RK3576_LLM),
        _path_check("reference RK3576 Qwen3-VL-4B vision", QWEN3_VL_4B_RK3576_VISION),
    ]
    checks.extend(_directory_member_check(RKNN_LLM_123_ROOT, REQUIRED_RKLLM_123_EXAMPLE_FILES, "rkllm123"))
    checks.extend(_tar_member_check(RKNN_LLM_TAR, REQUIRED_LEGACY_MULTIMODAL_EXAMPLE_FILES))
    return checks


def _is_required_conversion_check(check: ConversionCheck) -> bool:
    optional_names = (
        "reference RK3576",
        "example:",
    )
    return not check.name.startswith(optional_names)


def print_rk3588_qwen3_vl_conversion_check() -> int:
    checks = collect_rk3588_qwen3_vl_conversion_checks()
    headers = ("check", "status", "detail")
    rows = [(check.name, check.status, check.detail) for check in checks]
    widths = [max(len(str(row[index])) for row in (headers, *rows)) for index in range(len(headers))]
    print("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(str(value).ljust(widths[index]) for index, value in enumerate(row)))
    print()
    print("notes:")
    print("- Existing Qwen3-VL-4B files are RK3576 artifacts; they are not valid RK3588 outputs.")
    print("- RK3588 conversion requires the original HuggingFace Qwen3-VL-4B-Instruct source model.")
    print("- Use the packaged Qwen2-VL multimodal example as the closest conversion template.")
    print(f"- Default HuggingFace source path: {DEFAULT_QWEN3_VL_4B_HF_PATH}")
    return 0 if all(check.status == "ok" for check in checks if _is_required_conversion_check(check)) else 1


def _huggingface_resolve_url(filename: str) -> str:
    quoted = urllib.parse.quote(filename, safe="/")
    return f"https://huggingface.co/{QWEN3_VL_4B_HF_REPO}/resolve/main/{quoted}?download=true"


def _curl_download(destination: Path, url: str, range_header: str | None = None) -> None:
    partial = destination.with_name(f"{destination.name}.part")
    command = [
        "curl",
        "-L",
        "--fail",
        "--silent",
        "--show-error",
        "--connect-timeout",
        "30",
        "--max-time",
        "1800",
    ]
    if range_header:
        command.extend(["-r", range_header])
    else:
        command.extend(["-C", "-"])
    command.extend(["-o", str(partial), url])
    try:
        run(command, check=True)
    except CalledProcessError:
        print(f"partial file kept for resume: {partial}")
        raise
    partial.replace(destination)


def _download_chunk(chunk_file: Path, url: str, start: int, end: int, expected_size: int) -> None:
    if chunk_file.exists() and chunk_file.stat().st_size == expected_size:
        return
    last_error: Exception | None = None
    for attempt in range(1, 6):
        if chunk_file.exists():
            chunk_file.unlink()
        try:
            _curl_download(chunk_file, url, f"{start}-{end}")
            actual_size = chunk_file.stat().st_size
            if actual_size == expected_size:
                return
            raise RuntimeError(f"bad chunk size for {chunk_file}: expected {expected_size}, got {actual_size}")
        except Exception as error:
            last_error = error
            print(f"chunk retry {attempt}/5 for {chunk_file.name}: {error}")
    if last_error:
        raise last_error


def _download_chunked(destination: Path, url: str, total_size: int, chunk_size: int, workers: int) -> None:
    chunks_dir = destination.with_name(f"{destination.name}.chunks")
    chunks_dir.mkdir(exist_ok=True)
    ranges = []
    for index, start in enumerate(range(0, total_size, chunk_size)):
        end = min(start + chunk_size - 1, total_size - 1)
        ranges.append((index, start, end, end - start + 1))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                _download_chunk,
                chunks_dir / f"{index:05d}.part",
                url,
                start,
                end,
                expected_size,
            )
            for index, start, end, expected_size in ranges
        ]
        for completed, future in enumerate(as_completed(futures), start=1):
            future.result()
            print(f"chunk complete {completed}/{len(futures)} for {destination.name}")

    for index, _start, _end, expected_size in ranges:
        chunk_file = chunks_dir / f"{index:05d}.part"
        if not chunk_file.exists() or chunk_file.stat().st_size != expected_size:
            actual = chunk_file.stat().st_size if chunk_file.exists() else None
            raise RuntimeError(f"missing or bad chunk {chunk_file}: expected {expected_size}, got {actual}")

    partial_destination = destination.with_name(f"{destination.name}.assembling")
    assembled_size = partial_destination.stat().st_size if partial_destination.exists() else 0
    complete_chunk_count = assembled_size // chunk_size
    if assembled_size % chunk_size:
        complete_chunk_count = 0
        assembled_size = 0
    print(f"assemble {destination.name} from chunk {complete_chunk_count}/{len(ranges)}")
    with partial_destination.open("ab" if assembled_size else "wb") as output:
        for index, _start, _end, _expected_size in ranges:
            if index < complete_chunk_count:
                continue
            chunk_file = chunks_dir / f"{index:05d}.part"
            for attempt in range(1, 6):
                try:
                    with chunk_file.open("rb") as input_file:
                        shutil.copyfileobj(input_file, output, length=1024 * 1024)
                    output.flush()
                    break
                except OSError as error:
                    print(f"assemble retry {attempt}/5 for chunk {index:05d}: {error}")
                    time.sleep(2 * attempt)
                    if attempt == 5:
                        raise
    actual_size = partial_destination.stat().st_size
    if actual_size != total_size:
        raise RuntimeError(f"bad assembled size for {destination}: expected {total_size}, got {actual_size}")
    partial_destination.replace(destination)
    shutil.rmtree(chunks_dir)


def download_qwen3_vl_4b_source(
    target: Path = DEFAULT_QWEN3_VL_4B_HF_PATH,
    chunk_size: int = DEFAULT_CHUNK_SIZE_BYTES,
    workers: int = DEFAULT_DOWNLOAD_WORKERS,
) -> None:
    target.mkdir(parents=True, exist_ok=True)
    manifest = target / "download-manifest.txt"
    manifest.write_text(
        "\n".join(f"{name}\t{_huggingface_resolve_url(name)}" for name in QWEN3_VL_4B_HF_FILES) + "\n",
        encoding="utf-8",
    )
    (target / "SOURCE.md").write_text(
        "\n".join(
            [
                "# Qwen3-VL-4B-Instruct Hugging Face Source",
                "",
                f"- repo: `{QWEN3_VL_4B_HF_REPO}`",
                f"- revision checked: `{QWEN3_VL_4B_HF_REVISION}`",
                f"- local path: `{target}`",
                "",
                "Downloaded with resumable `curl -L -C -` requests.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    for name in QWEN3_VL_4B_HF_FILES:
        destination = target / name
        url = _huggingface_resolve_url(name)
        expected_size = QWEN3_VL_4B_HF_FILE_SIZES[name]
        if destination.exists() and destination.stat().st_size == expected_size:
            print(f"skip existing {name} ({destination.stat().st_size} bytes)")
            continue
        if destination.exists():
            print(f"replace incomplete {name} ({destination.stat().st_size} bytes, expected {expected_size})")
            destination.unlink()
        print(f"download {name}")
        if expected_size >= CHUNKED_DOWNLOAD_THRESHOLD_BYTES:
            _download_chunked(destination, url, expected_size, chunk_size, workers)
        else:
            _curl_download(destination, url)
            actual_size = destination.stat().st_size
            if actual_size != expected_size:
                raise RuntimeError(f"bad file size for {destination}: expected {expected_size}, got {actual_size}")


def print_download_qwen3_vl_4b_source(
    target: Path = DEFAULT_QWEN3_VL_4B_HF_PATH,
    chunk_size: int = DEFAULT_CHUNK_SIZE_BYTES,
    workers: int = DEFAULT_DOWNLOAD_WORKERS,
) -> int:
    download_qwen3_vl_4b_source(target, chunk_size=chunk_size, workers=workers)
    print(f"downloaded source model: {target}")
    print("next: ./scripts/edgectl rkllm-conversion-check")
    return 0


def _copytree_contents(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        destination = target / item.name
        if item.is_dir():
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(item, destination)
        else:
            shutil.copy2(item, destination)


def _patch_qwen3_vl_imgenc_probe(demo_root: Path) -> None:
    img_encoder = demo_root / "deploy" / "src" / "img_encoder.cpp"
    if not img_encoder.exists():
        img_encoder = demo_root / "src" / "img_encoder.cpp"
    if not img_encoder.exists():
        return

    source = img_encoder.read_text(encoding="utf-8")
    if "std::vector<float> img_vec(img_vec_len);" in source:
        return

    patched = source
    if "#include <vector>" not in patched:
        patched = patched.replace('#include <chrono>\n', '#include <chrono>\n#include <vector>\n')
    patched = re.sub(
        r"    float img_vec\[[^\]]+\];\n",
        "    size_t img_vec_len = static_cast<size_t>(rknn_app_ctx.model_image_token) * "
        "rknn_app_ctx.model_embed_size * rknn_app_ctx.io_num.n_output;\n"
        "    std::vector<float> img_vec(img_vec_len);\n",
        patched,
    )
    patched = patched.replace(
        "    ret = run_imgenc(&rknn_app_ctx, resized_img.data, img_vec);",
        "    ret = run_imgenc(&rknn_app_ctx, resized_img.data, img_vec.data());",
    )
    patched = patched.replace(
        "    file.write(reinterpret_cast<char*>(img_vec), sizeof(img_vec));",
        "    file.write(reinterpret_cast<char*>(img_vec.data()), img_vec.size() * sizeof(float));",
    )
    if patched != source:
        img_encoder.write_text(patched, encoding="utf-8")


def prepare_rk3588_qwen3_vl_workspace(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    if RKNN_LLM_123_ROOT.exists():
        example_root = RKNN_LLM_123_ROOT / "examples" / "multimodal_model_demo"
        wheel = RKNN_LLM_123_ROOT / RKLLM_123_WHEEL
        readme = RKNN_LLM_123_ROOT / "README.md"
        toolkit_version = "1.2.3"
    else:
        extracted = workspace / "_rknn_llm_extract"
        if extracted.exists():
            shutil.rmtree(extracted)
        extracted.mkdir()

        with tarfile.open(RKNN_LLM_TAR, "r:gz") as archive:
            members = [
                member
                for member in archive.getmembers()
                if any(member.name == wanted or member.name.startswith(f"{wanted}/") for wanted in LEGACY_WORKSPACE_MEMBERS)
            ]
            archive.extractall(extracted, members=members, filter="data")

        example_root = extracted / "rknn-llm" / "examples" / "rkllm_multimodel_demo"
        wheel = extracted / LEGACY_RKLLM_WHEEL
        readme = extracted / "rknn-llm" / "README.md"
        toolkit_version = "1.1.4"

    _copytree_contents(example_root, workspace / "qwen3_vl_4b_rk3588")
    demo_root = workspace / "qwen3_vl_4b_rk3588"
    _patch_qwen3_vl_imgenc_probe(demo_root)
    (demo_root / "data" / "make_input_embeds_for_quantize_qwen3.py").write_text(
        QWEN3_VL_INPUT_HELPER,
        encoding="utf-8",
    )
    (demo_root / "export" / "export_rkllm_qwen3_context.py").write_text(
        QWEN3_VL_RKLLM_CONTEXT_EXPORT,
        encoding="utf-8",
    )
    export_helper = demo_root / "run-qwen3-vl-rk3588-export.sh"
    export_helper.write_text(QWEN3_VL_EXPORT_HELPER, encoding="utf-8")
    export_helper.chmod(0o755)

    wheels_dir = workspace / "wheels"
    wheels_dir.mkdir(exist_ok=True)
    shutil.copy2(wheel, wheels_dir / wheel.name)
    shutil.copy2(readme, workspace / "rknn-llm-README.md")
    notes = Path(__file__).resolve().parents[2] / "docs" / "experiments" / "2026-06-28-rk3588-qwen3-vl-conversion-notes.md"
    if notes.exists():
        shutil.copy2(notes, workspace / "CONVERSION_NOTES.md")

    (workspace / "environment.yml").write_text(
        "\n".join(
            [
                "name: rkllm-qwen3-vl",
                "channels:",
                "  - conda-forge",
                "dependencies:",
                "  - python=3.10",
                "  - pip",
                "  - numpy",
                "  - pillow",
                "  - tqdm",
                "  - pytorch",
                "  - torchvision",
                "  - pip:",
                "      - rknn-toolkit2>=2.3.2",
                "      - transformers==4.55.2",
                "      - accelerate",
                "      - datasets",
                "      - qwen-vl-utils",
                f"      - ./wheels/rkllm_toolkit-{toolkit_version}-cp310-cp310-linux_x86_64.whl",
                "",
            ]
        ),
        encoding="utf-8",
    )

    (workspace / "README.md").write_text(
        "\n".join(
            [
                "# RK3588 Qwen3-VL-4B Conversion Workspace",
                "",
                "Run this on Linux x86_64 with enough disk space.",
                "",
                "```bash",
                "conda env create -f environment.yml",
                "conda activate rkllm-qwen3-vl",
                "```",
                "",
                f"RKLLM toolkit version: `{toolkit_version}`.",
                "",
                "For Qwen3-VL, use `export/export_vision.py --model_name=qwen3-vl --height=448 --width=448` with the 1.2.x example.",
                "",
                "Set model paths to the local Qwen3-VL-4B-Instruct HuggingFace source directory.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    if "extracted" in locals():
        shutil.rmtree(extracted)


def print_prepare_rk3588_qwen3_vl_workspace(workspace: Path) -> int:
    prepare_rk3588_qwen3_vl_workspace(workspace)
    print(f"prepared workspace: {workspace}")
    print("next: run this workspace on Linux x86_64 with enough free disk space")
    return 0
