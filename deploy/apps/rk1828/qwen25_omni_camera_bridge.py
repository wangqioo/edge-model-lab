#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
import secrets
import urllib.error
import urllib.request
from email.parser import BytesParser
from email.policy import default as email_policy
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8894
DEFAULT_BOARD_BASE_URL = "http://192.168.1.52:8892"
MAX_UPLOAD_BYTES = 12 * 1024 * 1024


class UploadedFile:
    def __init__(self, filename: str, content_type: str, data: bytes) -> None:
        self.filename = filename
        self.content_type = content_type
        self.data = data


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
        payload = part.get_payload(decode=True) or b""
        filename = part.get_filename()
        if filename:
            files[name] = UploadedFile(Path(filename).name, part.get_content_type(), payload)
        else:
            charset = part.get_content_charset() or "utf-8"
            fields[name] = payload.decode(charset, errors="replace")
    return fields, files


def health_payload(board_base_url: str) -> dict[str, Any]:
    return {"ok": True, "board_base_url": board_base_url}


def build_multipart_body(image_name: str, image_content_type: str, image_data: bytes, prompt: str) -> tuple[bytes, str]:
    boundary = "----qwen25camera" + secrets.token_hex(12)
    parts = [
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="image"; filename="{image_name}"\r\n'
            f"Content-Type: {image_content_type}\r\n\r\n"
        ).encode("utf-8")
        + image_data
        + b"\r\n",
        (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="prompt"\r\n'
            "Content-Type: text/plain; charset=utf-8\r\n\r\n"
            f"{prompt}\r\n"
        ).encode("utf-8"),
        f"--{boundary}--\r\n".encode("utf-8"),
    ]
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def render_camera_page(board_base_url: str) -> str:
    escaped_board = html.escape(board_base_url)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Qwen2.5 Camera Voice Bridge</title>
  <style>
    :root {{
      --bg: #f5f6f3;
      --panel: #ffffff;
      --ink: #20252b;
      --muted: #64707a;
      --line: #d7ded8;
      --accent: #0f766e;
      --accent-2: #2f5d7c;
      --danger: #a33b3b;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      display: grid;
      grid-template-columns: minmax(360px, 1.2fr) minmax(320px, .8fr);
      gap: 18px;
      width: min(1180px, calc(100vw - 32px));
      margin: 20px auto 32px;
    }}
    header {{
      grid-column: 1 / -1;
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 16px;
    }}
    h1 {{ margin: 0; font-size: 26px; letter-spacing: 0; }}
    .sub {{ color: var(--muted); margin: 4px 0 0; }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }}
    video, canvas {{
      width: 100%;
      aspect-ratio: 16 / 10;
      background: #111827;
      border-radius: 6px;
      object-fit: cover;
    }}
    canvas {{ display: none; }}
    textarea {{
      width: 100%;
      min-height: 118px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      font: inherit;
      color: var(--ink);
    }}
    .controls {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin-top: 10px;
    }}
    button {{
      min-height: 42px;
      border: 0;
      border-radius: 6px;
      padding: 0 12px;
      font: inherit;
      color: #fff;
      background: var(--accent);
      cursor: pointer;
    }}
    button.secondary {{ background: var(--accent-2); }}
    button.ghost {{ background: #59636e; }}
    button:disabled {{ opacity: .55; cursor: not-allowed; }}
    .status {{
      min-height: 24px;
      margin-top: 10px;
      color: var(--muted);
    }}
    .status.error {{ color: var(--danger); }}
    .history {{
      display: flex;
      flex-direction: column;
      gap: 10px;
      max-height: calc(100vh - 180px);
      overflow: auto;
    }}
    .turn {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: #fbfcfa;
    }}
    .turn img {{
      width: 120px;
      max-width: 35%;
      border-radius: 6px;
      float: right;
      margin-left: 10px;
    }}
    .answer {{ font-size: 17px; margin: 8px 0; }}
    pre {{
      clear: both;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      background: #eef2ee;
      border-radius: 6px;
      padding: 8px;
      color: var(--muted);
    }}
    @media (max-width: 860px) {{
      main {{ grid-template-columns: 1fr; }}
      header {{ align-items: start; flex-direction: column; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Qwen2.5-Omni-3B Camera Voice Bridge</h1>
        <p class="sub">Sensors from this computer. Inference from {escaped_board}. Audio is browser speech recognition/synthesis.</p>
      </div>
      <button class="ghost" id="startCamera">Start Camera</button>
    </header>
    <section>
      <video id="preview" autoplay playsinline muted></video>
      <canvas id="frame"></canvas>
      <div class="controls">
        <button class="secondary" id="listen">Listen</button>
        <button id="ask">Ask With Frame</button>
        <button class="ghost" id="speakToggle">Speak: On</button>
      </div>
      <p class="status" id="status">Open the camera, speak or type a prompt, then ask with the current frame.</p>
    </section>
    <section>
      <textarea id="prompt" placeholder="Speak or type your question"><image>请用中文描述你现在看到的画面，并回答我的问题。</textarea>
      <div class="history" id="history"></div>
    </section>
  </main>
  <script>
    const video = document.getElementById('preview');
    const canvas = document.getElementById('frame');
    const promptBox = document.getElementById('prompt');
    const statusBox = document.getElementById('status');
    const historyBox = document.getElementById('history');
    const askButton = document.getElementById('ask');
    const listenButton = document.getElementById('listen');
    const speakToggle = document.getElementById('speakToggle');
    let speakEnabled = true;
    let stream = null;

    function setStatus(text, isError = false) {{
      statusBox.textContent = text;
      statusBox.className = isError ? 'status error' : 'status';
    }}

    async function startCamera() {{
      stream = await navigator.mediaDevices.getUserMedia({{ video: true, audio: false }});
      video.srcObject = stream;
      setStatus('Camera is ready.');
    }}

    function speak(text) {{
      if (!speakEnabled || !('speechSynthesis' in window)) return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'zh-CN';
      window.speechSynthesis.speak(utterance);
    }}

    function appendTurn(imageUrl, prompt, payload) {{
      const turn = document.createElement('div');
      turn.className = 'turn';
      const metrics = (payload.metrics || []).join('\\n');
      turn.innerHTML = `
        <img src="${{imageUrl}}" alt="Captured frame">
        <div><strong>Prompt</strong></div>
        <div>${{escapeHtml(prompt)}}</div>
        <div class="answer">${{escapeHtml(payload.answer || payload.error || 'No answer')}}</div>
        <pre>${{escapeHtml(metrics)}}</pre>
      `;
      historyBox.prepend(turn);
    }}

    function escapeHtml(text) {{
      return String(text).replace(/[&<>"']/g, ch => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[ch]));
    }}

    async function askWithFrame() {{
      if (!stream) await startCamera();
      const width = video.videoWidth || 1280;
      const height = video.videoHeight || 720;
      canvas.width = width;
      canvas.height = height;
      canvas.getContext('2d').drawImage(video, 0, 0, width, height);
      const prompt = promptBox.value.trim() || '<image>请用中文描述你现在看到的画面。';
      askButton.disabled = true;
      setStatus('Sending frame to RK1828...');
      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.88));
      const imageUrl = URL.createObjectURL(blob);
      const form = new FormData();
      form.append('image', blob, 'frame.jpg');
      form.append('prompt', prompt);
      try {{
        const response = await fetch('/infer', {{ method: 'POST', body: form }});
        const payload = await response.json();
        appendTurn(imageUrl, prompt, payload);
        if (!payload.ok) throw new Error(payload.error || 'Inference failed');
        setStatus('Answer received.');
        speak(payload.answer || '');
      }} catch (error) {{
        setStatus(error.message || String(error), true);
      }} finally {{
        askButton.disabled = false;
      }}
    }}

    function startListening() {{
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {{
        setStatus('This browser does not expose SpeechRecognition. Type your prompt instead.', true);
        return;
      }}
      const recognition = new SpeechRecognition();
      recognition.lang = 'zh-CN';
      recognition.interimResults = true;
      recognition.continuous = false;
      recognition.onstart = () => setStatus('Listening...');
      recognition.onerror = event => setStatus(event.error || 'Speech recognition error', true);
      recognition.onresult = event => {{
        let text = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {{
          text += event.results[i][0].transcript;
        }}
        promptBox.value = text;
      }};
      recognition.onend = () => setStatus('Speech captured. Edit if needed, then ask with frame.');
      recognition.start();
    }}

    document.getElementById('startCamera').addEventListener('click', () => startCamera().catch(err => setStatus(err.message, true)));
    askButton.addEventListener('click', () => askWithFrame());
    listenButton.addEventListener('click', () => startListening());
    speakToggle.addEventListener('click', () => {{
      speakEnabled = !speakEnabled;
      speakToggle.textContent = `Speak: ${{speakEnabled ? 'On' : 'Off'}}`;
      if (!speakEnabled && 'speechSynthesis' in window) window.speechSynthesis.cancel();
    }});
  </script>
</body>
</html>"""


class BridgeHandler(BaseHTTPRequestHandler):
    server_version = "Qwen25CameraBridge/0.1"

    @property
    def board_base_url(self) -> str:
        return self.server.board_base_url  # type: ignore[attr-defined]

    def do_GET(self) -> None:
        if self.path == "/health":
            self.write_json(health_payload(self.board_base_url))
            return
        if self.path == "/" or self.path.startswith("/?"):
            self.write_html(render_camera_page(self.board_base_url))
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path != "/infer":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        if content_length <= 0 or content_length > MAX_UPLOAD_BYTES:
            self.write_json({"ok": False, "error": "Upload is empty or larger than 12 MB."}, HTTPStatus.BAD_REQUEST)
            return
        fields, files = parse_multipart(self.headers, self.rfile.read(content_length))
        image = files.get("image")
        prompt = fields.get("prompt", "")
        if image is None:
            self.write_json({"ok": False, "error": "Missing image upload."}, HTTPStatus.BAD_REQUEST)
            return
        body, content_type = build_multipart_body(image.filename, image.content_type, image.data, prompt)
        try:
            payload, status = forward_to_board(self.board_base_url, body, content_type)
        except Exception as exc:
            self.write_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_GATEWAY)
            return
        self.write_json(payload, HTTPStatus(status))

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


def forward_to_board(board_base_url: str, body: bytes, content_type: str) -> tuple[dict[str, Any], int]:
    request = urllib.request.Request(
        board_base_url.rstrip("/") + "/api/infer",
        data=body,
        headers={"Content-Type": content_type, "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=480) as response:
            return json.loads(response.read().decode("utf-8")), response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"ok": False, "error": raw}
        return payload, exc.code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.environ.get("QWEN25_CAMERA_HOST", DEFAULT_HOST))
    parser.add_argument("--port", type=int, default=int(os.environ.get("QWEN25_CAMERA_PORT", str(DEFAULT_PORT))))
    parser.add_argument("--board-base-url", default=os.environ.get("QWEN25_BOARD_BASE_URL", DEFAULT_BOARD_BASE_URL))
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), BridgeHandler)
    server.board_base_url = args.board_base_url  # type: ignore[attr-defined]
    print(f"listening on http://{args.host}:{args.port}; board={args.board_base_url}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
