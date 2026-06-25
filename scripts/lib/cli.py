from __future__ import annotations

import argparse
import sys

from .assets import asset_exists, asset_size_label, load_assets
from .bootstrap import bootstrap_rknn_lite
from .config import Device, load_devices
from .health import print_health
from .rknn import run_rknn_smoke
from .yolo import run_yolo_deploy, run_yolo_smoke


def _print_device_table(devices: dict[str, Device]) -> None:
    headers = ("id", "platform", "role", "backend", "ssh", "board")
    rows = [
        (
            device.id,
            device.platform,
            device.role,
            device.deployment_backend,
            f"{device.user}@{device.host}:{device.port}",
            device.board,
        )
        for device in devices.values()
    ]
    widths = [
        max(len(str(row[index])) for row in (headers, *rows))
        for index in range(len(headers))
    ]
    print("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(str(value).ljust(widths[index]) for index, value in enumerate(row)))


def _print_asset_table(platform: str | None = None) -> None:
    assets = load_assets()
    rows = []
    for asset in assets.values():
        if platform and asset.platform != platform:
            continue
        rows.append(
            (
                asset.id,
                asset.kind,
                asset.platform,
                asset.workload,
                asset.source,
                asset_size_label(asset),
                "yes" if asset_exists(asset) else "no",
            )
        )

    headers = ("id", "kind", "platform", "workload", "source", "bytes", "path_exists")
    if not rows:
        print("No model assets matched.")
        return
    widths = [
        max(len(str(row[index])) for row in (headers, *rows))
        for index in range(len(headers))
    ]
    print("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(str(value).ljust(widths[index]) for index, value in enumerate(row)))


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="edgectl")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="List configured edge devices")
    health_parser = subparsers.add_parser("health", help="Run read-only device health checks")
    health_parser.add_argument("target", help="Device id or 'all'")
    models_parser = subparsers.add_parser("models", help="List registered model assets")
    models_parser.add_argument("--platform", choices=("rk3576", "rk3588", "portable"), help="Filter assets by target platform")
    smoke_parser = subparsers.add_parser("rknn-smoke", help="Upload a registered RKNN asset and initialize RKNN Lite runtime")
    smoke_parser.add_argument("device", help="Device id")
    smoke_parser.add_argument("asset", help="Registered RKNN asset id")
    smoke_parser.add_argument(
        "--python",
        default=None,
        help="Python interpreter on the target device",
    )
    bootstrap_parser = subparsers.add_parser("rknn-bootstrap", help="Install the minimal RKNN Lite Python runtime on a device")
    bootstrap_parser.add_argument("target", help="Device id or 'all'")
    yolo_parser = subparsers.add_parser("yolo-smoke", help="Run the K7 RK3576 YOLOv5 vendor demo")
    yolo_parser.add_argument("device", help="Device id")
    deploy_yolo_parser = subparsers.add_parser("yolo-deploy", help="Install the RK3576 YOLOv5 demo under /opt/edge and start the systemd smoke unit")
    deploy_yolo_parser.add_argument("device", help="Device id")

    args = parser.parse_args(argv)
    devices = load_devices()
    assets = load_assets()

    if args.command == "list":
        _print_device_table(devices)
        return 0

    if args.command == "models":
        _print_asset_table(platform=args.platform)
        return 0

    if args.command == "health":
        if args.target == "all":
            exit_code = 0
            for device in devices.values():
                exit_code = max(exit_code, print_health(device))
            return exit_code
        device = devices.get(args.target)
        if not device:
            parser.error(f"Unknown device: {args.target}")
        return print_health(device)

    if args.command == "rknn-smoke":
        device = devices.get(args.device)
        if not device:
            parser.error(f"Unknown device: {args.device}")
        asset = assets.get(args.asset)
        if not asset:
            parser.error(f"Unknown asset: {args.asset}")
        return run_rknn_smoke(device, asset, args.python)

    if args.command == "rknn-bootstrap":
        if args.target == "all":
            exit_code = 0
            for device in devices.values():
                exit_code = max(exit_code, bootstrap_rknn_lite(device))
            return exit_code
        device = devices.get(args.target)
        if not device:
            parser.error(f"Unknown device: {args.target}")
        return bootstrap_rknn_lite(device)

    if args.command == "yolo-smoke":
        device = devices.get(args.device)
        if not device:
            parser.error(f"Unknown device: {args.device}")
        return run_yolo_smoke(device)

    if args.command == "yolo-deploy":
        device = devices.get(args.device)
        if not device:
            parser.error(f"Unknown device: {args.device}")
        return run_yolo_deploy(device)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
