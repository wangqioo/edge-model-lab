# RK3576 Python RKNN Service Baseline

Date: 2026-06-25

## Goal

Move beyond one-shot RKNN Lite initialization checks and deploy a long-running Python inference service on both RK3576 boards.

Targets:

- `linaro-rk3576`
- `lckfb-rk3576`

## Service Shape

The service is a local-only HTTP process managed by systemd:

- app: `/opt/edge/apps/rknn_service/edge_rknn_service.py`
- unit: `edge-rknn-python.service`
- bind: `127.0.0.1:18080`
- model: `/opt/edge/models/rk3576_resnet18_lite2.rknn`
- endpoints:
  - `GET /health`
  - `GET /infer/synthetic`
  - `GET /bench/synthetic?count=N`

Deployment command:

```bash
./scripts/edgectl rknn-service-deploy linaro-rk3576
./scripts/edgectl rknn-service-deploy lckfb-rk3576
```

Inspection commands:

```bash
./scripts/edgectl service-status linaro-rk3576 edge-rknn-python.service
./scripts/edgectl logs linaro-rk3576 edge-rknn-python.service --lines 80
./scripts/edgectl rknn-service-bench linaro-rk3576 --count 20
```

## Model Selection

Initial service testing used `rk3576_mobilenet_v2_lite2`, the RKNN Lite dynamic-shape example model. It loaded and initialized successfully, but inference aborted inside the RKNN runtime:

```text
terminate called after throwing an instance of 'std::out_of_range'
what(): vector::_M_range_check: __n (which is 18446744073709551615) >= this->size() (which is 3)
```

This happened in both the HTTP service path and a minimal same-thread Python script, so the root cause was not the HTTP server threading model.

The service baseline now uses `rk3576_resnet18_lite2`, a static-shape RKNN Lite example model. The service uses a synthetic NHWC zero tensor with shape `(1, 224, 224, 3)`.

## Results

`linaro-rk3576`:

```json
{"inference_count": 0, "init_ret": 0, "last_inference_ms": null, "load_init_ms": 163, "load_ret": 0, "model_path": "/opt/edge/models/rk3576_resnet18_lite2.rknn", "ok": true, "uptime_s": 1}
{"elapsed_ms": 14.522, "ok": true, "output_count": 1, "output_shapes": [[1, 1000]]}
```

`lckfb-rk3576`:

```json
{"inference_count": 0, "init_ret": 0, "last_inference_ms": null, "load_init_ms": 169, "load_ret": 0, "model_path": "/opt/edge/models/rk3576_resnet18_lite2.rknn", "ok": true, "uptime_s": 1}
{"elapsed_ms": 11.969, "ok": true, "output_count": 1, "output_shapes": [[1, 1000]]}
```

20-run synthetic benchmark after adding `/bench/synthetic`:

```text
linaro-rk3576: avg=10.389 ms, p50=9.666 ms, p95=14.993 ms, min=8.690 ms, max=14.993 ms
lckfb-rk3576: avg=6.241 ms, p50=7.418 ms, p95=10.825 ms, min=4.424 ms, max=10.825 ms
```

## Notes

- The unit currently runs as the board login user because the Python RKNN Lite environment is installed in that user's venv.
- `SupplementaryGroups=video render` is retained for device access.
- This is a local control-plane service baseline, not yet an externally exposed API.
- The dynamic-shape MobileNet inference failure should be kept as a compatibility issue to revisit before using dynamic-shape models as service workloads.

## Next Steps

1. Add temperature and memory snapshots around benchmark runs.
2. Move the Python venv under `/opt/edge/venv` once the package installation path is stable.
3. Add a model-specific input adapter layer before serving YOLO, VLM, or RKLLM workloads.
4. Decide whether service lifecycle should be `start-only` for tests or `enable --now` for persistent deployments.
