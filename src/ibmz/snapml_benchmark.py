"""IBM LinuxONE Snap ML Acceleration Benchmark.
Tests IBM z16/z17 Telum on-chip AI acceleration (nnpa) using Snap ML vs Scikit-Learn.
"""
import os
import sys
import time
import warnings
from pathlib import Path
from importlib.metadata import version

# Suppress runtime warnings from snapml
warnings.filterwarnings("ignore", category=RuntimeWarning, module="snapml")

# Ensure user site packages are accessible if not in default sys.path
user_site = os.path.expanduser("~/.local/lib/python3.12/site-packages")
if user_site not in sys.path:
    sys.path.insert(0, user_site)

def run_snapml_benchmark(n_samples: int = 50000, n_features: int = 20, n_estimators: int = 50):
    print("=" * 65)
    print("      IBM LinuxONE (s390x) Snap ML Hardware Benchmark")
    print("=" * 65)

    try:
        import snapml
        print(f"[+] Snap ML Version: {version('snapml')}")
    except ImportError:
        print("[!] Snap ML not installed. Install with: python3 -m pip install --break-system-packages snapml")
        return None

    from sklearn.datasets import make_classification
    from sklearn.ensemble import RandomForestClassifier as SklearnRF
    from snapml import RandomForestClassifier as SnapRF

    # Determine thread count (Snap ML requires n_jobs > 0)
    num_threads = os.cpu_count() or 3
    print(f"[+] Utilizing {num_threads} CPU/hardware threads for benchmark.")

    print(f"[+] Generating synthetic dataset ({n_samples:,} samples, {n_features} features)...")
    X, y = make_classification(n_samples=n_samples, n_features=n_features, random_state=42)

    # 1. Scikit-Learn Benchmark
    print("[*] Benchmarking standard Scikit-Learn...")
    t0 = time.time()
    sk_model = SklearnRF(n_estimators=n_estimators, random_state=42, n_jobs=num_threads).fit(X, y)
    t_sk = time.time() - t0
    print(f"    -> Scikit-Learn CPU Time: {t_sk:.3f}s")

    # 2. Snap ML Benchmark
    print("[*] Benchmarking IBM Snap ML (Telum accelerated)...")
    t0 = time.time()
    snap_model = SnapRF(n_estimators=n_estimators, random_state=42, n_jobs=num_threads).fit(X, y)
    t_snap = time.time() - t0
    print(f"    -> Snap ML Execution Time: {t_snap:.3f}s")

    speedup = t_sk / max(t_snap, 1e-6)
    print("-" * 65)
    print(f"[>>>] SPEEDUP: {speedup:.2f}x faster with IBM Snap ML")
    print("=" * 65)
    return {"sklearn_time": t_sk, "snapml_time": t_snap, "speedup": speedup}

if __name__ == "__main__":
    run_snapml_benchmark()
