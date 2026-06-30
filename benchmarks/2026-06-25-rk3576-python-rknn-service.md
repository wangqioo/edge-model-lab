# RK3576 Python RKNN Service Benchmark

Date: 2026-06-25

## Workload

- Service: `edge-rknn-python.service`
- Endpoint: `GET /bench/synthetic?count=20`
- Model: `rk3576_resnet18_lite2.rknn`
- Runtime: RKNN Lite Python service, systemd-managed
- Input: synthetic NHWC zero tensor, shape `(1, 224, 224, 3)`, batch size 1
- Output shape: `[[1, 1000]]`

## Commands

```bash
./scripts/edgectl rknn-service-bench linaro-rk3576 --count 20
./scripts/edgectl rknn-service-bench lckfb-rk3576 --count 20
```

## Results

| Device | Count | Min ms | Avg ms | P50 ms | P95 ms | Max ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `linaro-rk3576` | 20 | 8.690 | 10.389 | 9.666 | 14.993 | 14.993 |
| `lckfb-rk3576` | 20 | 4.424 | 6.241 | 7.418 | 10.825 | 10.825 |

## Raw Output

```json
{"avg_ms": 10.389, "count": 20, "max_ms": 14.993, "min_ms": 8.69, "ok": true, "output_shapes": [[1, 1000]], "p50_ms": 9.666, "p95_ms": 14.993}
{"avg_ms": 6.241, "count": 20, "max_ms": 10.825, "min_ms": 4.424, "ok": true, "output_shapes": [[1, 1000]], "p50_ms": 7.418, "p95_ms": 10.825}
```

## Notes

- The benchmark serializes inference through one RKNNLite instance.
- Results do not yet include temperature, memory, CPU, or NPU utilization snapshots.
- The unexpectedly faster `lckfb-rk3576` result should be rechecked after adding thermal and governor metadata.
