from __future__ import annotations

import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

from .config import Device
from .ssh import run_scp_to_device, run_ssh


YOLO_ARCHIVE = Path(
    "/Users/wq/Documents/ZSPACE/sata11-15850752485/百度网盘下载/K7 rk3576/3-SoftwareData/Linux_rknn_yolov5/rknn_yolov5_demo_Linux_rk3576.zip"
)
YOLO_DIR_NAME = "rknn_yolov5_demo_Linux_rk3576"
YOLO_ASSET_ID = "k7_rk3576_yolov5s_demo"
REMOTE_BASE = "/tmp/edge-model-lab-yolo"


def _extract_demo(output_dir: Path) -> Path:
    subprocess.run(
        ["bsdtar", "-xf", str(YOLO_ARCHIVE), "-C", str(output_dir)],
        check=True,
        capture_output=True,
        text=True,
    )
    demo_dir = output_dir / YOLO_DIR_NAME
    if not demo_dir.exists():
        raise FileNotFoundError(f"{YOLO_DIR_NAME} not found in archive")
    return demo_dir


def _upload_demo(device: Device, demo_dir: Path, remote_dir: str) -> tuple[int, str]:
    complete_check = (
        f"test -x {shlex.quote(remote_dir)}/rknn_yolov5_demo && "
        f"test -f {shlex.quote(remote_dir)}/model/RK3576/yolov5s-640-640.rknn && "
        f"test -f {shlex.quote(remote_dir)}/model/bus.jpg && "
        f"test -f {shlex.quote(remote_dir)}/lib/librknnrt.so"
    )
    check_code, _ = run_ssh(device, complete_check, timeout_seconds=20)
    if check_code == 0:
        return 0, ""

    mkdir_code, mkdir_output = run_ssh(
        device,
        f"rm -rf {shlex.quote(remote_dir)} && mkdir -p {shlex.quote(remote_dir)}",
        timeout_seconds=20,
    )
    if mkdir_code != 0:
        return mkdir_code, mkdir_output

    remote_rsync_code, _ = run_ssh(device, "command -v rsync >/dev/null 2>&1", timeout_seconds=20)
    if shutil.which("rsync") and remote_rsync_code == 0:
        command = [
            "rsync",
            "-az",
            "--delete",
            "-e",
            (
                f"ssh -p {device.port} "
                "-o PreferredAuthentications=password "
                "-o PubkeyAuthentication=no "
                "-o NumberOfPasswordPrompts=1 "
                "-o StrictHostKeyChecking=no"
            ),
            f"{demo_dir}/",
            f"{device.user}@{device.host}:{remote_dir}/",
        ]
        import os

        env = os.environ.copy()
        if device.password_env:
            password = os.environ.get(device.password_env)
            if password and shutil.which("sshpass"):
                command = ["sshpass", "-e", *command]
                env["SSHPASS"] = password
        completed = subprocess.run(command, check=False, capture_output=True, env=env, text=True)
        if completed.returncode == 0:
            chmod_code, chmod_output = run_ssh(
                device,
                f"chmod +x {shlex.quote(remote_dir)}/rknn_yolov5_demo {shlex.quote(remote_dir)}/rknn_yolov5_video_demo",
                timeout_seconds=20,
            )
            return chmod_code, chmod_output
        return completed.returncode, completed.stdout + completed.stderr

    layout_code, layout_output = run_ssh(
        device,
        (
            f"mkdir -p {shlex.quote(remote_dir)}/lib "
            f"{shlex.quote(remote_dir)}/model/RK3576"
        ),
        timeout_seconds=20,
    )
    if layout_code != 0:
        return layout_code, layout_output

    uploads = [
        ("rknn_yolov5_demo", f"{remote_dir}/rknn_yolov5_demo"),
        ("rknn_yolov5_video_demo", f"{remote_dir}/rknn_yolov5_video_demo"),
        ("lib/libmk_api.so", f"{remote_dir}/lib/libmk_api.so"),
        ("lib/librga.so", f"{remote_dir}/lib/librga.so"),
        ("lib/librknnrt.so", f"{remote_dir}/lib/librknnrt.so"),
        ("lib/librockchip_mpp.so", f"{remote_dir}/lib/librockchip_mpp.so"),
        ("model/bus.jpg", f"{remote_dir}/model/bus.jpg"),
        ("model/coco_80_labels_list.txt", f"{remote_dir}/model/coco_80_labels_list.txt"),
        ("model/RK3576/yolov5s-640-640.rknn", f"{remote_dir}/model/RK3576/yolov5s-640-640.rknn"),
    ]
    for local_relative, remote_path in uploads:
        code, output = run_scp_to_device(device, demo_dir / local_relative, remote_path)
        if code != 0:
            return code, output

    return run_ssh(
        device,
        f"chmod +x {shlex.quote(remote_dir)}/rknn_yolov5_demo {shlex.quote(remote_dir)}/rknn_yolov5_video_demo",
        timeout_seconds=20,
    )


def run_yolo_smoke(device: Device) -> int:
    if device.platform != "rk3576":
        print(f"YOLO smoke asset targets rk3576, device {device.id} is {device.platform}")
        return 2

    remote_dir = f"{REMOTE_BASE}/{YOLO_ASSET_ID}"
    with tempfile.TemporaryDirectory(prefix="edge-yolo-demo-") as temp_name:
        temp_dir = Path(temp_name)
        try:
            demo_dir = _extract_demo(temp_dir)
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            print(f"failed to extract YOLO demo: {exc}")
            return 2

        upload_code, upload_output = _upload_demo(device, demo_dir, remote_dir)
        if upload_code != 0:
            print(upload_output.rstrip())
            return upload_code

    remote_command = f"""
set -eu
cd {shlex.quote(remote_dir)}
echo "## files"
ls -lh rknn_yolov5_demo model/RK3576/yolov5s-640-640.rknn model/bus.jpg lib/librknnrt.so
echo
echo "## runtime"
strings lib/librknnrt.so | grep -m1 'librknnrt version' || true
echo
echo "## demo"
LD_LIBRARY_PATH={shlex.quote(remote_dir)}/lib ./rknn_yolov5_demo model/RK3576/yolov5s-640-640.rknn model/bus.jpg
"""
    print(f"===== YOLO smoke {device.id} {YOLO_ASSET_ID} =====")
    code, output = run_ssh(device, remote_command, timeout_seconds=120)
    if output:
        print(output.rstrip())
    return code
