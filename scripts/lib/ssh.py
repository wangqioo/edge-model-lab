from __future__ import annotations

import os
import shutil
import subprocess

from .config import Device


def run_ssh(
    device: Device,
    remote_command: str,
    timeout_seconds: int = 20,
    stdin: str | None = None,
) -> tuple[int, str]:
    command = [
        "ssh",
        "-p",
        str(device.port),
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "ConnectTimeout=8",
        f"{device.user}@{device.host}",
    ]
    if remote_command:
        command.append(remote_command)

    env = os.environ.copy()
    if device.password_env:
        password = os.environ.get(device.password_env)
        if password:
            sshpass = shutil.which("sshpass")
            if not sshpass:
                return 127, f"sshpass is required because {device.password_env} is set in local config\n"
            command = [
                sshpass,
                "-e",
                "ssh",
                "-p",
                str(device.port),
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "ConnectTimeout=8",
                f"{device.user}@{device.host}",
            ]
            if remote_command:
                command.append(remote_command)
            env["SSHPASS"] = password

    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            env=env,
            input=stdin,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return 124, f"Timed out after {timeout_seconds}s\n"

    return completed.returncode, completed.stdout + completed.stderr
