from __future__ import annotations

import argparse
import sys

from .config import Device, load_devices
from .health import print_health


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


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="edgectl")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="List configured edge devices")
    health_parser = subparsers.add_parser("health", help="Run read-only device health checks")
    health_parser.add_argument("target", help="Device id or 'all'")

    args = parser.parse_args(argv)
    devices = load_devices()

    if args.command == "list":
        _print_device_table(devices)
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

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))

