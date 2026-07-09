# Qwen2.5-Omni VLM Test Console Design

## Goal

Provide a separate browser-based test console for the already deployed
Qwen2.5-Omni-3B Vision+LLM demo on the RK3588 + RK1828K host.

## Scope

The console supports image upload plus a text prompt. It returns the text
answer printed by the Qwen2.5-Omni demo and basic timing output when present.

This is not a replacement for the current Qwen3-VL chat service. It must not
modify ports `8888` or `8899`, the Qwen3-VL model files, or the public FRP
mapping.

## Architecture

Add one small stdlib-only Python HTTP app under `deploy/apps/rk1828/`. It serves
an HTML form, accepts multipart image uploads, writes the image to a temporary
directory, then invokes `/home/orangepi/lincaigui/run-qwen25-omni-3b-vlm.sh`.

The RK1828 cannot safely run Qwen3-VL and Qwen2.5-Omni at the same time. The
app serializes requests with one process lock. For each inference request it
stops `rkllm3-server.service`, runs Qwen2.5-Omni, and starts
`rkllm3-server.service` again in a `finally` path.

## Deployment

Install the app on the RK3588 host as:

```text
/home/orangepi/lincaigui/qwen25-omni-vlm-web/qwen25_omni_vlm_web.py
```

Track a systemd unit in:

```text
deploy/systemd/rk1828/qwen25-omni-vlm-web.service
```

The service listens on a separate local-network port, `8892`, and does not touch
the existing public chat endpoint.

## Error Handling

The app reports command failures, timeout failures, and missing uploads in the
HTML response. The Qwen3-VL service restart is attempted even if Qwen2.5-Omni
fails.

## Testing

Local unit tests cover:

- extracting the generated answer from demo stdout
- extracting timing lines from demo stdout
- rejecting non-image multipart uploads
- preserving safe HTML escaping in rendered responses

Board verification covers:

- service starts on `127.0.0.1:8892`
- `/health` returns JSON
- Qwen3-VL health on `8888` is still OK before and after a manual Qwen2.5-Omni
  request
