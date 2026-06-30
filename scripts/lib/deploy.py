from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
from pathlib import Path

from .assets import load_assets
from .config import Device, load_devices
from .rknn import run_rknn_smoke
from .rknn_service import bench_rknn_service, deploy_rknn_service
from .ssh import run_chunked_upload_to_device, run_remote_sudo, run_scp_to_device, run_ssh


QWEN3_VL_DEMO_DIR = Path(
    "/Users/wq/Documents/ZSPACE/sata11-15850752485/百度网盘下载/立创·泰山派RK3576开发板资料/8.【立创·泰山派3】Ai应用/Qwen3-VL-2B-Instruct/2025-12-31/demo_Linux_aarch64"
)
QWEN3_VL_VISION = Path(
    "/Users/wq/Documents/ZSPACE/sata11-15850752485/百度网盘下载/立创·泰山派RK3576开发板资料/8.【立创·泰山派3】Ai应用/Qwen3-VL-2B-Instruct/2025-12-31/qwen3-vl_vision_rk3576.rknn"
)
QWEN3_VL_LLM = Path(
    "/Users/wq/Documents/ZSPACE/sata11-15850752485/百度网盘下载/立创·泰山派RK3576开发板资料/8.【立创·泰山派3】Ai应用/Qwen3-VL-2B-Instruct/2025-12-31/qwen3-vl-2b-instruct_w8a8_rk3576.rkllm"
)
QWEN3_VL_REMOTE_DIR = "/opt/edge/apps/rkllm_qwen3_vl_2b"
QWEN3_VL_REMOTE_TMP = "/tmp/edge-model-lab-rkllm-qwen3-vl"
QWEN3_VL_REMOTE_CMD = (
    "/opt/edge/apps/rkllm_qwen3_vl_2b/demo /opt/edge/apps/rkllm_qwen3_vl_2b/demo.jpg "
    "/opt/edge/models/qwen3-vl_vision_rk3576.rknn "
    "/opt/edge/models/qwen3-vl-2b-instruct_w8a8_rk3576.rkllm 64 2048 0"
)
QWEN3_VL_DEVICE_IDS = {"lckfb-rk3576", "linaro-rk3576"}

RK3588_RKLLM_DIR = Path(
    "/Users/wq/Documents/ZSPACE/sata11-15850752485/百度网盘下载/香橙派RK3588S/官方工具/RKLLM工具包"
)
RK3588_RKLLM_RUNTIME = RK3588_RKLLM_DIR / "RKLLM官网文件/rknn-llm.tar.gz"
RK3588_RKLLM_DEMO = RK3588_RKLLM_DIR / "转换后的模型/llm_demo"
RK3588_RKLLM_MODEL = RK3588_RKLLM_DIR / "转换后的模型/Qwen1_5.rkllm"
RK3588_RKLLM_REMOTE_DIR = "/opt/edge/apps/rkllm_text_smoke"
RK3588_RKLLM_REMOTE_TMP = "/tmp/edge-model-lab-rkllm-text"
RK3588_RKLLM_REMOTE_MODEL = "/opt/edge/models/Qwen1_5.rkllm"
RK3588_QWEN3_VL_REMOTE_ROOT = "/home/orangepi/edge-model-lab/qwen3-vl-rk3588"
RK3588_QWEN3_VL_LLM = "qwen3-vl-4b-instruct_w8a8_rk3588.rkllm"
RK3588_QWEN3_VL_VISION = "qwen3-vl_vision_rk3588.rknn"


def deploy_llm_device(device: Device) -> int:
    if device.id in QWEN3_VL_DEVICE_IDS:
        return deploy_rkllm_device(device)
    if device.id == "orange-rk3588":
        return deploy_rk3588_rkllm_text_smoke(device)
    else:
        print(f"no llm deploy recipe for {device.id}")
        return 2


def deploy_device(device: Device) -> int:
    if device.platform == "rk3576":
        return deploy_rknn_service(device)
    if device.platform == "rk3588":
        return deploy_rknn_service(device)
    print(f"no deploy recipe for {device.platform}")
    return 2


def deploy_rkllm_device(device: Device) -> int:
    if device.id not in QWEN3_VL_DEVICE_IDS:
        print(f"no rkllm deploy recipe for {device.id}")
        return 2

    with tempfile.TemporaryDirectory(prefix="edge-rkllm-qwen3-vl-") as temp_name:
        temp_dir = Path(temp_name)
        uploads = [
            (QWEN3_VL_DEMO_DIR / "demo", temp_dir / "demo"),
            (QWEN3_VL_DEMO_DIR / "demo.jpg", temp_dir / "demo.jpg"),
            (QWEN3_VL_DEMO_DIR / "imgenc", temp_dir / "imgenc"),
            (QWEN3_VL_DEMO_DIR / "lib" / "librkllmrt.so", temp_dir / "librkllmrt.so"),
            (QWEN3_VL_DEMO_DIR / "lib" / "librknnrt.so", temp_dir / "librknnrt.so"),
            (QWEN3_VL_VISION, QWEN3_VL_REMOTE_TMP + "/qwen3-vl_vision_rk3576.rknn", True),
            (QWEN3_VL_LLM, QWEN3_VL_REMOTE_TMP + "/qwen3-vl-2b-instruct_w8a8_rk3576.rkllm", True),
        ]
        for local_path, temp_target in uploads[:5]:
            temp_target.write_bytes(Path(local_path).read_bytes())

        mkdir_code, mkdir_output = run_ssh(device, f"mkdir -p {QWEN3_VL_REMOTE_TMP}", timeout_seconds=20)
        if mkdir_code != 0:
            print(mkdir_output.rstrip())
            return mkdir_code
        for temp_target in temp_dir.iterdir():
            scp_code, scp_output = run_scp_to_device(device, temp_target, f"{QWEN3_VL_REMOTE_TMP}/{temp_target.name}")
            if scp_code != 0:
                print(scp_output.rstrip())
                return scp_code
        for local_path, remote_path, use_chunked in uploads[5:]:
            if use_chunked:
                upload_code, upload_output = run_chunked_upload_to_device(device, Path(local_path), remote_path)
            else:
                upload_code, upload_output = run_scp_to_device(device, Path(local_path), remote_path)
            if upload_code != 0:
                print(upload_output.rstrip())
                return upload_code

    install_command = f"""
set -eu
test -d {shlex.quote(QWEN3_VL_REMOTE_TMP)}
sudo sh -c 'set -eu
mkdir -p /opt/edge /opt/edge/apps /opt/edge/models /opt/edge/logs /opt/edge/run {shlex.quote(QWEN3_VL_REMOTE_DIR)} {shlex.quote(QWEN3_VL_REMOTE_DIR)}/lib
cp {shlex.quote(QWEN3_VL_REMOTE_TMP)}/demo {shlex.quote(QWEN3_VL_REMOTE_DIR)}/demo
cp {shlex.quote(QWEN3_VL_REMOTE_TMP)}/demo.jpg {shlex.quote(QWEN3_VL_REMOTE_DIR)}/demo.jpg
cp {shlex.quote(QWEN3_VL_REMOTE_TMP)}/imgenc {shlex.quote(QWEN3_VL_REMOTE_DIR)}/imgenc
cp {shlex.quote(QWEN3_VL_REMOTE_TMP)}/librkllmrt.so {shlex.quote(QWEN3_VL_REMOTE_DIR)}/lib/librkllmrt.so
cp {shlex.quote(QWEN3_VL_REMOTE_TMP)}/librknnrt.so {shlex.quote(QWEN3_VL_REMOTE_DIR)}/lib/librknnrt.so
cp {shlex.quote(QWEN3_VL_REMOTE_TMP)}/qwen3-vl_vision_rk3576.rknn /opt/edge/models/qwen3-vl_vision_rk3576.rknn
cp {shlex.quote(QWEN3_VL_REMOTE_TMP)}/qwen3-vl-2b-instruct_w8a8_rk3576.rkllm /opt/edge/models/qwen3-vl-2b-instruct_w8a8_rk3576.rkllm
chmod 0755 {shlex.quote(QWEN3_VL_REMOTE_DIR)}/demo {shlex.quote(QWEN3_VL_REMOTE_DIR)}/imgenc
chown -R edge:edge /opt/edge/apps /opt/edge/models /opt/edge/logs /opt/edge/run {shlex.quote(QWEN3_VL_REMOTE_DIR)}'
"""
    install_code, install_output = run_remote_sudo(device, install_command, timeout_seconds=60)
    if install_output:
        print(install_output.rstrip())
    if install_code != 0:
        return install_code

    smoke_command = f"""
set -eu
cd {shlex.quote(QWEN3_VL_REMOTE_DIR)}
echo "## files"
ls -lh demo demo.jpg imgenc lib/librkllmrt.so lib/librknnrt.so /opt/edge/models/qwen3-vl_vision_rk3576.rknn /opt/edge/models/qwen3-vl-2b-instruct_w8a8_rk3576.rkllm
echo
echo "## demo"
(printf '0\\nexit\\n' | env LD_LIBRARY_PATH={shlex.quote(QWEN3_VL_REMOTE_DIR)}/lib {QWEN3_VL_REMOTE_CMD}) || true
"""
    print(f"===== RKLLM Qwen3-VL smoke {device.id} =====")
    code, output = run_ssh(device, "sh -s", timeout_seconds=300, stdin=smoke_command)
    if output:
        print(output.rstrip())
    return code


def deploy_rk3588_rkllm_text_smoke(device: Device) -> int:
    if device.id != "orange-rk3588":
        print(f"no rk3588 rkllm text smoke recipe for {device.id}")
        return 2

    with tempfile.TemporaryDirectory(prefix="edge-rk3588-rkllm-") as temp_name:
        temp_dir = Path(temp_name)
        runtime_lib = temp_dir / "librkllmrt.so"
        with runtime_lib.open("wb") as runtime_output:
            subprocess.run(
                [
                    "tar",
                    "-xOf",
                    str(RK3588_RKLLM_RUNTIME),
                    "rknn-llm/rkllm-runtime/Linux/librkllm_api/aarch64/librkllmrt.so",
                ],
                check=True,
                stdout=runtime_output,
            )

        mkdir_code, mkdir_output = run_ssh(device, f"mkdir -p {RK3588_RKLLM_REMOTE_TMP}", timeout_seconds=20)
        if mkdir_code != 0:
            print(mkdir_output.rstrip())
            return mkdir_code

        uploads = [
            (RK3588_RKLLM_DEMO, f"{RK3588_RKLLM_REMOTE_TMP}/llm_demo"),
            (runtime_lib, f"{RK3588_RKLLM_REMOTE_TMP}/librkllmrt.so"),
        ]
        for local_path, remote_path in uploads:
            code, output = run_scp_to_device(device, Path(local_path), remote_path)
            if code != 0:
                print(output.rstrip())
                return code

        code, output = run_chunked_upload_to_device(
            device,
            RK3588_RKLLM_MODEL,
            f"{RK3588_RKLLM_REMOTE_TMP}/Qwen1_5.rkllm",
        )
        if code != 0:
            print(output.rstrip())
            return code

    install_command = f"""
set -eu
test -d {shlex.quote(RK3588_RKLLM_REMOTE_TMP)}
mkdir -p /opt/edge /opt/edge/apps /opt/edge/models /opt/edge/logs {shlex.quote(RK3588_RKLLM_REMOTE_DIR)} {shlex.quote(RK3588_RKLLM_REMOTE_DIR)}/lib
cp {shlex.quote(RK3588_RKLLM_REMOTE_TMP)}/llm_demo {shlex.quote(RK3588_RKLLM_REMOTE_DIR)}/llm_demo
cp {shlex.quote(RK3588_RKLLM_REMOTE_TMP)}/librkllmrt.so {shlex.quote(RK3588_RKLLM_REMOTE_DIR)}/lib/librkllmrt.so
cp {shlex.quote(RK3588_RKLLM_REMOTE_TMP)}/Qwen1_5.rkllm {shlex.quote(RK3588_RKLLM_REMOTE_MODEL)}
chmod 0755 {shlex.quote(RK3588_RKLLM_REMOTE_DIR)}/llm_demo
"""
    install_code, install_output = run_remote_sudo(device, install_command, timeout_seconds=120)
    if install_output:
        print(install_output.rstrip())
    if install_code != 0:
        return install_code

    smoke_command = f"""
set -eu
cd {shlex.quote(RK3588_RKLLM_REMOTE_DIR)}
echo "## files"
ls -lh llm_demo lib/librkllmrt.so {shlex.quote(RK3588_RKLLM_REMOTE_MODEL)}
echo
echo "## demo"
(printf '4\\nexit\\n' | env LD_LIBRARY_PATH={shlex.quote(RK3588_RKLLM_REMOTE_DIR)}/lib taskset f0 ./llm_demo {shlex.quote(RK3588_RKLLM_REMOTE_MODEL)} 64 512) || true
"""
    print(f"===== RK3588 RKLLM text smoke {device.id} =====")
    code, output = run_ssh(device, "sh -s", timeout_seconds=300, stdin=smoke_command)
    if output:
        print(output.rstrip())
    return code


def run_rk3588_qwen3_vl_smoke(device: Device) -> int:
    if device.id != "orange-rk3588":
        print(f"rk3588 qwen3-vl smoke targets orange-rk3588, device {device.id} is {device.platform}")
        return 2

    sudo_password = os.environ.get(device.password_env, "") if device.password_env else ""
    demo_dir = f"{RK3588_QWEN3_VL_REMOTE_ROOT}/demo"
    vision_model = f"{RK3588_QWEN3_VL_REMOTE_ROOT}/models/{RK3588_QWEN3_VL_VISION}"
    llm_model = f"{RK3588_QWEN3_VL_REMOTE_ROOT}/models/{RK3588_QWEN3_VL_LLM}"
    smoke_command = f"""
set -eu
sudo_with_password() {{
  printf '%s\\n' {shlex.quote(sudo_password)} | sudo -S -p '' "$@"
}}
echo "## system"
uname -a
echo "## rknpu"
rknpu_version=$(sudo_with_password cat /sys/kernel/debug/rknpu/version)
echo "$rknpu_version"
test "$rknpu_version" = "RKNPU driver: v0.9.8"
echo "## cma"
grep -E "CmaTotal|CmaFree" /proc/meminfo
echo "## files"
test -x {shlex.quote(demo_dir)}/demo
test -x {shlex.quote(demo_dir)}/imgenc
test -r {shlex.quote(vision_model)}
test -r {shlex.quote(llm_model)}
ls -lh {shlex.quote(demo_dir)}/demo {shlex.quote(demo_dir)}/imgenc {shlex.quote(vision_model)} {shlex.quote(llm_model)}
echo "## vision"
cd {shlex.quote(demo_dir)}
rm -f img_vec.bin
LD_LIBRARY_PATH=./lib timeout 120 ./imgenc {shlex.quote(vision_model)} demo.jpg 3
test -s img_vec.bin
sha256sum img_vec.bin
echo "## multimodal"
printf '0\\n' | LD_LIBRARY_PATH=./lib timeout 90 ./demo demo.jpg {shlex.quote(vision_model)} {shlex.quote(llm_model)} 32 4096 3 '<|vision_start|>' '<|vision_end|>' '<|image_pad|>' || rc=$?
rc=${{rc:-0}}
if [ "$rc" != "0" ] && [ "$rc" != "124" ]; then
  exit "$rc"
fi
sudo_with_password pkill -x demo 2>/dev/null || true
sudo_with_password pkill -x timeout 2>/dev/null || true
echo "## final cma"
grep -E "CmaTotal|CmaFree" /proc/meminfo
"""
    print(f"===== RK3588 Qwen3-VL smoke {device.id} =====")
    code, output = run_ssh(device, smoke_command, timeout_seconds=240)
    if output:
        print(output.rstrip())
    if code != 0:
        return code
    if "rkllm init success" not in output or "robot:" not in output:
        print("Qwen3-VL smoke did not show rkllm init success and robot output")
        return 1
    return 0


def bench_device(device: Device) -> int:
    if device.platform in {"rk3576", "rk3588"}:
        return bench_rknn_service(device, 20)
    print(f"no benchmark recipe for {device.platform}")
    return 2


def deploy_all() -> int:
    devices = load_devices()
    exit_code = 0
    for device in devices.values():
        result = deploy_device(device)
        if result != 0:
            exit_code = max(exit_code, result)
    return exit_code


def bench_all() -> int:
    devices = load_devices()
    exit_code = 0
    for device in devices.values():
        result = bench_device(device)
        if result != 0:
            exit_code = max(exit_code, result)
    return exit_code
