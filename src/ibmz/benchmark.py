"""ONNX Runtime Latency Benchmark for IBM Z Telum Readiness.
Evaluates single-transaction and batch inference latency over 100,000 policy renewal events.
"""
import time
import json
import platform
from pathlib import Path
from typing import Dict, Any
import numpy as np
import pandas as pd
import onnxruntime as ort
from src import config
from src.ibmz import scoring

BENCHMARK_PATH = config.DATA_DIR / "latency_benchmark.json"


def run_benchmark(n_policies: int = 100000, n_single_calls: int = 10000, seed: int = 42) -> Dict[str, Any]:
    """Score single transactions (10k calls with preprocessing) and 100k batch throughput via ONNX Runtime.
    Label clearly: Ran on laptop CPU, not Telum. Expected to be deployable on Telum via ONNX/IBM Z Deep Learning Compiler; not tested on Telum.
    """
    onnx_path = config.DATA_DIR / "risk_model.onnx"
    if not onnx_path.exists():
        print("[benchmark] ONNX model missing; exporting from XGBoost...")
        scoring.export_onnx(str(onnx_path))

    sess = ort.InferenceSession(str(onnx_path))
    input_name = sess.get_inputs()[0].name

    rng = np.random.default_rng(seed)
    feats = config.ENV_FEATURES
    n_feats = len(feats)

    # 1. Warm-up
    dummy = np.zeros((1, n_feats), dtype=np.float32)
    for _ in range(25):
        _ = sess.run(None, {input_name: dummy})

    # 2. Single-row ONNX latency (batch size 1, 10,000 calls, INCLUDING preprocessing)
    # Generate 10,000 raw policy/tract attribute dictionaries to measure realistic end-to-end scoring pipeline
    raw_inputs = []
    for _ in range(n_single_calls):
        raw_inputs.append({f: float(rng.uniform(0.0, 1.0)) for f in feats})

    single_latencies_ms = []
    for raw in raw_inputs:
        t0 = time.perf_counter()
        # Preprocessing: convert dict attributes into model input matrix
        arr = np.array([[raw[f] for f in feats]], dtype=np.float32)
        # Inference call
        _ = sess.run(None, {input_name: arr})
        t1 = time.perf_counter()
        single_latencies_ms.append((t1 - t0) * 1000.0)

    single_latencies_arr = np.array(single_latencies_ms)

    # 3. Batch throughput for 100,000 rows
    X_100k = rng.random((n_policies, n_feats), dtype=np.float32)
    t_batch_start = time.perf_counter()
    _ = sess.run(None, {input_name: X_100k})
    t_batch_end = time.perf_counter()
    batch_total_sec = t_batch_end - t_batch_start
    batch_throughput = n_policies / max(batch_total_sec, 1e-6)

    results = {
        "benchmark_timestamp": pd.Timestamp.now("UTC").isoformat(),
        "single_row_benchmark": {
            "batch_size": 1,
            "calls_measured": n_single_calls,
            "includes_preprocessing": True,
            "latency_p50_ms": float(np.percentile(single_latencies_arr, 50)),
            "latency_p90_ms": float(np.percentile(single_latencies_arr, 90)),
            "latency_p95_ms": float(np.percentile(single_latencies_arr, 95)),
            "latency_p99_ms": float(np.percentile(single_latencies_arr, 99)),
            "latency_mean_ms": float(np.mean(single_latencies_arr)),
            "latency_min_ms": float(np.min(single_latencies_arr)),
            "latency_max_ms": float(np.max(single_latencies_arr)),
        },
        "batch_throughput_benchmark": {
            "total_rows_scored": n_policies,
            "total_time_sec": float(batch_total_sec),
            "throughput_rows_per_sec": float(batch_throughput),
        },
        "hardware_environment": {
            "label": "laptop CPU, not Telum",
            "platform": platform.platform(),
            "processor": platform.processor(),
            "is_telum": False,
        },
        "deployment_assessment": "expected to be deployable on Telum via ONNX/IBM Z Deep Learning Compiler; not tested on Telum",
        "honesty_note": (
            "Ran on laptop CPU, not Telum. Results do not prove Telum performance. "
            "Model is expected to be deployable on Telum via ONNX/IBM Z Deep Learning Compiler; not tested on Telum."
        )
    }

    BENCHMARK_PATH.write_text(json.dumps(results, indent=2))
    p50 = results["single_row_benchmark"]["latency_p50_ms"]
    p99 = results["single_row_benchmark"]["latency_p99_ms"]
    print(f"[benchmark] Single-row latency (10k calls + prep): p50={p50:.3f}ms, p99={p99:.3f}ms")
    print(f"[benchmark] Batch throughput (100k rows): {batch_throughput:,.0f} rows/sec")
    print("[benchmark] Hardware: laptop CPU, not Telum")
    print("[benchmark] Deployment: expected to be deployable on Telum via ONNX/IBM Z Deep Learning Compiler; not tested on Telum")
    return results


if __name__ == "__main__":
    run_benchmark()
