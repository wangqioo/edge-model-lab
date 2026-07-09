# Qwen2.5 Camera Voice Bridge Design

## Goal

Turn the Qwen2.5-Omni-3B VLM test console into a usable camera and voice
assistant experience that uses the user's computer sensors.

## Scope

The browser page runs on `localhost` so camera and microphone permissions work
without HTTPS. It captures the user's local camera preview, uses browser speech
recognition to turn speech into text, sends one captured frame plus text to the
RK3588/RK1828 Qwen2.5-Omni VLM service, then uses browser speech synthesis to
read the text answer aloud.

This does not make the RK1828 Qwen2.5-Omni model consume raw audio. The current
validated RKNN3 package still contains only Vision+LLM files.

## Architecture

Add a local bridge server:

```text
Mac browser localhost page
-> localhost camera bridge
-> RK3588 qwen25-omni-vlm-web.service /api/infer
-> RK1828 Qwen2.5-Omni Vision+LLM demo
```

The board service keeps its existing HTML form and gains a JSON endpoint,
`POST /api/infer`, for programmatic clients. The local bridge serves the camera
UI and proxies uploads to the board JSON endpoint.

## User Experience

The page has a large camera preview, a prompt box, a microphone button, a send
button, a speak toggle, and a conversation history. The user can speak a prompt,
edit it, capture the current frame, and hear the answer read aloud.

## Constraints

Qwen2.5-Omni and the existing Qwen3-VL service share the RK1828. The board JSON
endpoint uses the same serialized inference path as the current test console:
it briefly stops `rkllm3-server.service`, runs Qwen2.5-Omni, then starts
`rkllm3-server.service` again.

## Verification

Local unit tests cover JSON payload formatting, multipart forwarding, and the
camera page containing the required browser APIs. Manual verification covers
opening the localhost page, camera permission, speech recognition availability,
one image+prompt request, voice playback, and restoration of the Qwen3-VL
health endpoint.
