from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .config import PROJECT_ROOT


ASSETS_FILE = PROJECT_ROOT / "models" / "assets.yaml"


@dataclass(frozen=True)
class ModelAsset:
    id: str
    kind: str
    platform: str
    workload: str
    source: str
    path: str
    archive_member: str | None
    size_bytes: int | None
    smoke_input: str
    notes: tuple[str, ...]


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def load_assets() -> dict[str, ModelAsset]:
    raw = _read_yaml(ASSETS_FILE)
    raw_assets = raw.get("assets", {})
    if not isinstance(raw_assets, dict):
        raise ValueError("models/assets.yaml must contain an 'assets' mapping")

    assets: dict[str, ModelAsset] = {}
    for asset_id, values in raw_assets.items():
        if not isinstance(values, dict):
            raise ValueError(f"Asset {asset_id} must be a mapping")
        notes = values.get("notes", [])
        if notes is None:
            notes = []
        if not isinstance(notes, list):
            raise ValueError(f"Asset {asset_id} notes must be a list")
        size = values.get("size_bytes")
        assets[asset_id] = ModelAsset(
            id=asset_id,
            kind=str(values["kind"]),
            platform=str(values["platform"]),
            workload=str(values["workload"]),
            source=str(values["source"]),
            path=str(values["path"]),
            archive_member=values.get("archive_member"),
            size_bytes=int(size) if size is not None else None,
            smoke_input=str(values.get("smoke_input", "")),
            notes=tuple(str(note) for note in notes),
        )
    return assets


def asset_exists(asset: ModelAsset) -> bool:
    return Path(asset.path).exists()


def asset_size_label(asset: ModelAsset) -> str:
    if asset.size_bytes is None:
        path = Path(asset.path)
        if path.exists() and path.is_file():
            return str(path.stat().st_size)
        return "unknown"
    return str(asset.size_bytes)
