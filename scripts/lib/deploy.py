from __future__ import annotations

from .assets import load_assets
from .config import Device, load_devices
from .rknn import run_rknn_smoke
from .rknn_service import bench_rknn_service, deploy_rknn_service


def deploy_device(device: Device) -> int:
    if device.platform == "rk3576":
        return deploy_rknn_service(device)
    if device.platform == "rk3588":
        assets = load_assets()
        asset = assets.get("rk3588_resnet18_lite2")
        if not asset:
            print("missing rk3588_resnet18_lite2 asset")
            return 2
        return run_rknn_smoke(device, asset, None)
    print(f"no deploy recipe for {device.platform}")
    return 2


def bench_device(device: Device) -> int:
    if device.platform == "rk3576":
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
