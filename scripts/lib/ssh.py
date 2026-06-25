from __future__ import annotations

import os
import shutil
import subprocess
import shlex
from pathlib import Path

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


def run_scp_to_device(device: Device, local_path: Path, remote_path: str) -> tuple[int, str]:
    command = [
        "scp",
        "-P",
        str(device.port),
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "ConnectTimeout=8",
        "-o",
        "PreferredAuthentications=password",
        "-o",
        "PubkeyAuthentication=no",
        "-o",
        "NumberOfPasswordPrompts=1",
        str(local_path),
        f"{device.user}@{device.host}:{remote_path}",
    ]

    env = os.environ.copy()
    if device.password_env:
        password = os.environ.get(device.password_env)
        if password:
            sshpass = shutil.which("sshpass")
            if not sshpass:
                return 127, f"sshpass is required because {device.password_env} is set in local config\n"
            command = [sshpass, "-e", *command]
            env["SSHPASS"] = password

    completed = subprocess.run(command, check=False, capture_output=True, env=env, text=True)
    return completed.returncode, completed.stdout + completed.stderr


def run_remote_sudo(
    device: Device,
    remote_command: str,
    timeout_seconds: int = 20,
) -> tuple[int, str]:
    password = ""
    if device.password_env:
        password = os.environ.get(device.password_env, "")
    command = f"sudo -S -p '' sh -lc {shlex.quote(remote_command)}"
    return run_ssh(device, command, timeout_seconds=timeout_seconds, stdin=(password + "\n") if password else None)
