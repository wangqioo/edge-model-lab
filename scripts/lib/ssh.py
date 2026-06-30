from __future__ import annotations

import os
import shutil
import subprocess
import shlex
import tempfile
import time
from pathlib import Path

from .config import Device


def run_ssh(
    device: Device,
    remote_command: str,
    timeout_seconds: int = 20,
    stdin: str | None = None,
) -> tuple[int, str]:
    if device.password_env and not os.environ.get(device.password_env):
        return 126, f"missing required environment variable: {device.password_env}\n"

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
            "-o",
            "PreferredAuthentications=password",
            "-o",
            "PubkeyAuthentication=no",
            "-o",
            "NumberOfPasswordPrompts=1",
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


def run_scp_to_device(
    device: Device,
    local_path: Path,
    remote_path: str,
    max_retries: int = 3,
    pause_seconds: float = 1.5,
) -> tuple[int, str]:
    command = [
        "scp",
        "-O",
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

    last_output = ""
    for _ in range(max_retries):
        completed = subprocess.run(command, check=False, capture_output=True, env=env, text=True)
        last_output = completed.stdout + completed.stderr
        if completed.returncode == 0:
            return 0, last_output
        time.sleep(pause_seconds)
    return completed.returncode, last_output


def run_chunked_upload_to_device(
    device: Device,
    local_path: Path,
    remote_path: str,
    chunk_bytes: int = 16 * 1024 * 1024,
    max_retries: int = 3,
    pause_seconds: float = 0.2,
) -> tuple[int, str]:
    if chunk_bytes < 1024 * 1024:
        return 2, "chunk_bytes must be >= 1048576\n"

    remote_dir = str(Path(remote_path).parent)
    remote_name = Path(remote_path).name
    remote_tmp_dir = f"{remote_dir}/.{remote_name}.parts"
    local_size = local_path.stat().st_size

    existing_code, existing_output = run_ssh(
        device,
        (
            "python3 - <<'EOF'\n"
            "from pathlib import Path\n"
            f"p = Path({remote_path!r})\n"
            f"expected = {local_size}\n"
            "if p.exists():\n"
            "    size = p.stat().st_size\n"
            "    print(f'remote_bytes={size}')\n"
            "    raise SystemExit(0 if size == expected else 42)\n"
            "raise SystemExit(43)\n"
            "EOF"
        ),
        timeout_seconds=20,
    )
    if existing_code == 0:
        return 0, existing_output

    prepare_code, prepare_output = run_ssh(
        device,
        (
            f"mkdir -p {shlex.quote(remote_tmp_dir)} && "
            f"rm -f {shlex.quote(remote_path)}"
        ),
        timeout_seconds=30,
    )
    if prepare_code != 0:
        return prepare_code, prepare_output

    total_parts = (local_size + chunk_bytes - 1) // chunk_bytes
    prefix_code, prefix_output = run_ssh(
        device,
        (
            "python3 - <<'EOF'\n"
            "from pathlib import Path\n"
            f"parts_dir = Path({remote_tmp_dir!r})\n"
            f"total = {total_parts}\n"
            f"chunk_bytes = {chunk_bytes}\n"
            f"local_size = {local_size}\n"
            "valid = 0\n"
            "for index in range(total):\n"
            "    expected = chunk_bytes\n"
            "    if index == total - 1:\n"
            "        expected = local_size - (chunk_bytes * index)\n"
            "    part = parts_dir / f'{index:06d}.part'\n"
            "    if not part.exists() or part.stat().st_size != expected:\n"
            "        break\n"
            "    valid += 1\n"
            "print(valid)\n"
            "EOF"
        ),
        timeout_seconds=60,
    )
    if prefix_code != 0:
        return prefix_code, prefix_output
    valid_prefix = int(prefix_output.strip().splitlines()[-1] or "0")
    cleanup_code, cleanup_output = run_ssh(
        device,
        (
            "python3 - <<'EOF'\n"
            "from pathlib import Path\n"
            f"parts_dir = Path({remote_tmp_dir!r})\n"
            f"valid_prefix = {valid_prefix}\n"
            "for part in parts_dir.glob('*.part'):\n"
            "    try:\n"
            "        index = int(part.stem)\n"
            "    except ValueError:\n"
            "        part.unlink(missing_ok=True)\n"
            "        continue\n"
            "    if index >= valid_prefix:\n"
            "        part.unlink(missing_ok=True)\n"
            "EOF"
        ),
        timeout_seconds=60,
    )
    if cleanup_code != 0:
        return cleanup_code, cleanup_output

    index = valid_prefix
    with local_path.open("rb") as source:
        if valid_prefix:
            source.seek(valid_prefix * chunk_bytes)
        while True:
            data = source.read(chunk_bytes)
            if not data:
                break
            with tempfile.NamedTemporaryFile(prefix="edge-upload-chunk-", suffix=".bin", delete=False) as temp_file:
                temp_file.write(data)
                temp_chunk = Path(temp_file.name)
            remote_chunk = f"{remote_tmp_dir}/{index:06d}.part"
            try:
                uploaded = False
                last_output = ""
                verify_code, verify_output = run_ssh(
                    device,
                    (
                        "python3 - <<'EOF'\n"
                        "from pathlib import Path\n"
                        f"p = Path({remote_chunk!r})\n"
                        f"expected = {len(data)}\n"
                        "raise SystemExit(0 if p.exists() and p.stat().st_size == expected else 42)\n"
                        "EOF"
                    ),
                    timeout_seconds=20,
                )
                if verify_code == 0:
                    uploaded = True
                for _ in range(max_retries):
                    if uploaded:
                        break
                    code, output = run_scp_to_device(device, temp_chunk, remote_chunk)
                    last_output = output
                    if code != 0:
                        time.sleep(pause_seconds)
                        continue
                    verify_code, verify_output = run_ssh(
                        device,
                        (
                            "python3 - <<'EOF'\n"
                            "from pathlib import Path\n"
                            f"p = Path({remote_chunk!r})\n"
                            f"expected = {len(data)}\n"
                            "print(p.exists(), p.stat().st_size if p.exists() else -1)\n"
                            "raise SystemExit(0 if p.exists() and p.stat().st_size == expected else 42)\n"
                            "EOF"
                        ),
                        timeout_seconds=20,
                    )
                    if verify_code == 0:
                        uploaded = True
                        break
                    last_output = verify_output or last_output
                    time.sleep(pause_seconds)
                if not uploaded:
                    return 42, last_output
            finally:
                temp_chunk.unlink(missing_ok=True)
            index += 1
            time.sleep(pause_seconds)

    finalize_script = (
        "set -eu\n"
        "python3 - <<'EOF'\n"
        "from pathlib import Path\n"
        f"parts_dir = Path({remote_tmp_dir!r})\n"
        f"target = Path({remote_path!r})\n"
        f"expected = {local_size}\n"
        "with target.open('wb') as dst:\n"
        "    for part in sorted(parts_dir.glob('*.part')):\n"
        "        with part.open('rb') as src:\n"
        "            while True:\n"
        "                chunk = src.read(1024 * 1024)\n"
        "                if not chunk:\n"
        "                    break\n"
        "                dst.write(chunk)\n"
        "size = target.stat().st_size\n"
        "print(f'assembled_bytes={size}')\n"
        "if size != expected:\n"
        "    raise SystemExit(41)\n"
        "EOF\n"
        f"rm -f {shlex.quote(remote_tmp_dir)}/*.part\n"
    )
    finalize_code, finalize_output = run_ssh(
        device,
        "sh -s",
        timeout_seconds=max(120, index * 20),
        stdin=finalize_script,
    )
    return finalize_code, finalize_output


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
