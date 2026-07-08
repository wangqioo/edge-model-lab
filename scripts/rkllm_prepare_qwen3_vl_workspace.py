#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from lib.rkllm_conversion import print_prepare_rk3588_qwen3_vl_workspace


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", type=Path, help="Output workspace directory on a disk with enough free space")
    args = parser.parse_args()
    return print_prepare_rk3588_qwen3_vl_workspace(args.workspace)


if __name__ == "__main__":
    raise SystemExit(main())
