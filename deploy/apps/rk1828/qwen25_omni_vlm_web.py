#!/usr/bin/env python3
from __future__ import annotations

import argparse
from email.parser import BytesParser
from email.policy import default as email_policy
import html
import json
import os
import subprocess
import tempfile
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8892
DEFAULT_PROMPT = "<image>请用中文简短描述这张图片。"
DEFAULT_RUN_SCRIPT = "/home/orangepi/lincaigui/run-qwen25-omni-3b-vlm.sh"
DEFAULT_MODEL_SERVICE = "rkllm3-server.service"
DEFAULT_WEB_SERVICE = "rkclaw-web.service"
DEFAULT_TIMEOUT_SEC = 420
MAX_UPLOAD_BYTES = 12 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/x-ms-bmp",
    "application/octet-stream",
}
NOISE_PREFIXES = (
    "-->",
    "I ",
    "D ",
    "E ",
    "W ",
    "rknn",
    "RKLLM",
    "load ",
    "init_",
    "core ",
    "The ",
    "Qwen2.5-Omni audio",
)

inference_lock = threading.Lock()


class UploadedFile:
    def __init__(self, filename: str, content_type: str, data: bytes) -> None:
        self.filename = filename
        self.content_type = content_type
        self.data = data


def allowed_upload(filename: str, content_type: str) -> bool:
    suffix = Path(filename or "").suffix.lower()
    return suffix in ALLOWED_EXTENSIONS and content_type in ALLOWED_CONTENT_TYPES


def parse_demo_output(stdout: str) -> dict[str, Any]:
    metrics: list[str] = []
    answer_candidates: list[str] = []

    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if set(line) == {"-"}:
            continue
        if "Finished" in line:
            continue
        if line.startswith("Stage") or "Total Time" in line or "Tokens per Second" in line:
            continue
        if line.startswith(("Prefill", "Generate", "Vision latency")):
            metrics.append(line)
            continue
        if any(line.startswith(prefix) for prefix in NOISE_PREFIXES):
            continue
        if "latency =" in line or "tokens/s" in line:
            continue
        answer_candidates.append(line)

    answer = answer_candidates[-1] if answer_candidates else ""
    return {"answer": answer, "metrics": metrics, "raw": stdout}


def parse_multipart(headers: Any, body: bytes) -> tuple[dict[str, str], dict[str, UploadedFile]]:
    content_type = headers.get("Content-Type", "")
    raw = b"Content-Type: " + content_type.encode("utf-8") + b"\r\nMIME-Version: 1.0\r\n\r\n" + body
    message = BytesParser(policy=email_policy).parsebytes(raw)
    fields: dict[str, str] = {}
    files: dict[str, UploadedFile] = {}

    if not message.is_multipart():
        return fields, files

    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        filename = part.get_filename()
        payload = part.get_payload(decode=True) or b""
        if filename:
            files[name] = UploadedFile(filename=filename, content_type=part.get_content_type(), data=payload)
        else:
            charset = part.get_content_charset() or "utf-8"
            fields[name] = payload.decode(charset, errors="replace")
    return fields, files


def render_page(result: dict[str, Any] | None = None, error: str | None = None, busy: bool = False) -> str:
    answer = html.escape(str((result or {}).get("answer", "")))
    raw = html.escape(str((result or {}).get("raw", "")))
    metrics = result.get("metrics", []) if result else []
    metrics_html = "\n".join(html.escape(str(line)) for line in metrics)
    error_html = html.escape(error or "")
    busy_html = "<p class=\"notice\">RK1828 is busy. Try again after the current inference ends.</p>" if busy else ""
    result_html = ""
    if result:
        result_html = f"""
        <section class="result">
          <h2>Answer</h2>
          <p>{answer or "No answer line was detected. See raw output."}</p>
          <h2>Metrics</h2>
          <pre>{metrics_html or "No metrics were detected."}</pre>
          <details>
            <summary>Raw output</summary>
            <pre>{raw}</pre>
          </details>
        </section>
        """
    if error_html:
        result_html = f"<section class=\"error\"><h2>Error</h2><pre>{error_html}</pre></section>" + result_html

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Qwen2.5-Omni-3B VLM</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f7f4;
      --panel: #ffffff;
      --ink: #1f2933;
      --muted: #68737d;
      --line: #d8ddd8;
      --accent: #116466;
      --danger: #9d2a2a;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      width: min(960px, calc(100vw - 32px));
      margin: 28px auto 48px;
    }}
    h1 {{ margin: 0 0 20px; font-size: 28px; letter-spacing: 0; }}
    h2 {{ margin: 0 0 10px; font-size: 16px; letter-spacing: 0; }}
    form, .result, .error, .notice {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      margin: 14px 0;
    }}
    label {{ display: block; margin: 12px 0 6px; color: var(--muted); }}
    input[type="file"], textarea {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      background: #fff;
      color: var(--ink);
      font: inherit;
    }}
    textarea {{ min-height: 96px; resize: vertical; }}
    button {{
      margin-top: 14px;
      border: 0;
      border-radius: 6px;
      background: var(--accent);
      color: white;
      min-height: 40px;
      padding: 0 16px;
      font: inherit;
      cursor: pointer;
    }}
    pre {{
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      background: #f2f4f1;
      border-radius: 6px;
      padding: 12px;
    }}
    .error {{ border-color: #e0b0b0; color: var(--danger); }}
    .notice {{ color: var(--muted); }}
  </style>
</head>
<body>
  <main>
    <h1>Qwen2.5-Omni-3B VLM</h1>
    {busy_html}
    <form action="/infer" method="post" enctype="multipart/form-data">
      <label for="image">Image</label>
      <input id="image" name="image" type="file" accept="image/*" required>
      <label for="prompt">Prompt</label>
      <textarea id="prompt" name="prompt">{html.escape(DEFAULT_PROMPT)}</textarea>
      <button type="submit">Run</button>
    </form>
    {result_html}
  </main>
</body>
</html>"""


class Qwen25Handler(BaseHTTPRequestHandler):
    server_version = "Qwen25OmniVlmWeb/0.1"

    def do_GET(self) -> None:
        if self.path == "/health":
            self.write_json({"ok": True, "busy": inference_lock.locked()})
            return
        if self.path == "/" or self.path.startswith("/?"):
            self.write_html(render_page(busy=inference_lock.locked()))
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path not in {"/infer", "/api/infer"}:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not inference_lock.acquire(blocking=False):
            if self.path == "/api/infer":
                self.write_json({"ok": False, "error": "Another inference request is already running."}, HTTPStatus.CONFLICT)
            else:
                self.write_html(
                    render_page(busy=True, error="Another inference request is already running."),
                    HTTPStatus.CONFLICT,
                )
            return
        try:
            self.handle_infer()
        finally:
            inference_lock.release()

    def handle_infer(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        if content_length <= 0 or content_length > MAX_UPLOAD_BYTES:
            self.write_infer_error("Upload is empty or larger than 12 MB.", HTTPStatus.BAD_REQUEST)
            return

        body = self.rfile.read(content_length)
        fields, files = parse_multipart(self.headers, body)
        image_field = files.get("image")
        prompt = fields.get("prompt", DEFAULT_PROMPT) or DEFAULT_PROMPT
        if image_field is None or not image_field.filename:
            self.write_infer_error("Missing image upload.", HTTPStatus.BAD_REQUEST)
            return

        filename = Path(image_field.filename).name
        content_type = image_field.content_type
        if not allowed_upload(filename, content_type):
            self.write_infer_error(f"Unsupported upload type: {filename} ({content_type}).", HTTPStatus.BAD_REQUEST)
            return

        with tempfile.TemporaryDirectory(prefix="qwen25-omni-vlm-") as tmpdir:
            image_path = Path(tmpdir) / filename
            with image_path.open("wb") as fh:
                fh.write(image_field.data)
            result = run_inference(str(image_path), prompt)

        status = HTTPStatus.OK if result["returncode"] == 0 else HTTPStatus.INTERNAL_SERVER_ERROR
        if self.path == "/api/infer":
            self.write_json(build_infer_payload(result), status)
        else:
            error = None if result["returncode"] == 0 else f"Qwen2.5-Omni failed with return code {result['returncode']}."
            self.write_html(render_page(result=parse_demo_output(result["stdout"]), error=error), status)

    def write_infer_error(self, message: str, status: HTTPStatus) -> None:
        if self.path == "/api/infer":
            self.write_json({"ok": False, "error": message}, status)
        else:
            self.write_html(render_page(error=message), status)

    def write_html(self, body: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def write_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, fmt: str, *args: Any) -> None:
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)


def systemctl(action: str, service: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["systemctl", action, service], text=True, capture_output=True, check=False)


def run_inference(image_path: str, prompt: str) -> dict[str, Any]:
    run_script = os.environ.get("QWEN25_OMNI_RUN_SCRIPT", DEFAULT_RUN_SCRIPT)
    model_service = os.environ.get("QWEN25_OMNI_MODEL_SERVICE", DEFAULT_MODEL_SERVICE)
    web_service = os.environ.get("QWEN25_OMNI_WEB_SERVICE", DEFAULT_WEB_SERVICE)
    timeout = int(os.environ.get("QWEN25_OMNI_TIMEOUT_SEC", str(DEFAULT_TIMEOUT_SEC)))

    try:
        systemctl("stop", model_service)
        proc = subprocess.run(
            [run_script, image_path, prompt],
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode": 124,
            "stdout": exc.stdout or "",
            "stderr": f"Timed out after {timeout} seconds.",
        }
    finally:
        for service in services_to_start_after_inference(model_service, web_service):
            start_proc = systemctl("start", service)
            if start_proc.returncode != 0:
                print(start_proc.stderr, flush=True)


def services_to_start_after_inference(model_service: str, web_service: str | None) -> list[str]:
    services = [model_service]
    if web_service:
        services.append(web_service)
    return services


def build_infer_payload(result: dict[str, Any]) -> dict[str, Any]:
    returncode = int(result.get("returncode", 1))
    parsed = parse_demo_output(str(result.get("stdout", "")))
    payload: dict[str, Any] = {
        "ok": returncode == 0,
        "returncode": returncode,
        "answer": parsed["answer"],
        "metrics": parsed["metrics"],
        "raw": parsed["raw"],
        "stderr": str(result.get("stderr", "")),
    }
    if returncode != 0:
        payload["error"] = f"Qwen2.5-Omni failed with return code {returncode}."
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.environ.get("QWEN25_OMNI_WEB_HOST", DEFAULT_HOST))
    parser.add_argument("--port", type=int, default=int(os.environ.get("QWEN25_OMNI_WEB_PORT", str(DEFAULT_PORT))))
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Qwen25Handler)
    print(f"listening on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
