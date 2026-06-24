from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEVICES_FILE = PROJECT_ROOT / "devices.yaml"
LOCAL_FILE = PROJECT_ROOT / "devices.local.yaml"


@dataclass(frozen=True)
class Device:
    id: str
    host: str
    port: int
    user: str
    role: str
    platform: str
    board: str
    deployment_backend: str
    report: str
    password_env: str | None = None


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def load_devices() -> dict[str, Device]:
    raw = _read_yaml(DEVICES_FILE)
    local = _read_yaml(LOCAL_FILE)
    raw_devices = raw.get("devices", {})
    if not isinstance(raw_devices, dict):
        raise ValueError("devices.yaml must contain a 'devices' mapping")

    local_auth = local.get("auth", {})
    if local_auth is None:
        local_auth = {}
    if not isinstance(local_auth, dict):
        raise ValueError("devices.local.yaml auth must be a mapping")

    devices: dict[str, Device] = {}
    for device_id, values in raw_devices.items():
        if not isinstance(values, dict):
            raise ValueError(f"Device {device_id} must be a mapping")
        auth_values = local_auth.get(device_id, {})
        if auth_values is None:
            auth_values = {}
        if not isinstance(auth_values, dict):
            raise ValueError(f"Auth override for {device_id} must be a mapping")

        devices[device_id] = Device(
            id=device_id,
            host=str(values["host"]),
            port=int(values["port"]),
            user=str(values["user"]),
            role=str(values["role"]),
            platform=str(values["platform"]),
            board=str(values["board"]),
            deployment_backend=str(values["deployment_backend"]),
            report=str(values["report"]),
            password_env=auth_values.get("password_env"),
        )
    return devices

