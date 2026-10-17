"""Snap ML Benchmark on IBM LinuxONE / Host.
Measures:
1. RF training time on synthetic data (50,000 samples, 20 features): Scikit-Learn vs IBM Snap ML.
2. Inference latency on real risk model dataset: XGBoost vs Snap ML (if installed).
"""
import os
import sys
import time
import warnings
import platform
import subprocess
from pathlib import Path
from importlib.metadata import version

# Suppress runtime warnings from snapml
warnings.filterwarnings("ignore", category=RuntimeWarning, module="snapml")

# Ensure user site packages are accessible if not in default sys.path
user_site = os.path.expanduser("~/.local/lib/python3.12/site-packages")
if user_site not in sys.path:
    sys.path.insert(0, user_site)

def has_telum_nnpa() -> bool:
    """Check if IBM Telum NNPA (Neural Network Processing Assist) accelerator flag is present."""
    try:
        res = subprocess.run("lscpu", shell=True, capture_output=True, text=True, timeout=5)
        return "nnpa" in res.stdout.lower()
    except Exception:
        return False


def run_snapml_benchmark(n_samples: int = 50000, n_features: int = 20, n_estimators: int = 50):
    telum_active = has_telum_nnpa()
    accel_label = "Telum NNPA Hardware Verified" if telum_active else "Standard CPU / Multi-threaded"

    print("=" * 72)
    print("  Benchmark: RF Training Time on Synthetic Data (sklearn vs Snap ML)")
    print(f"  Execution Platform: {platform.system()} ({platform.machine()})")
    print(f"  Hardware Accelerator Status: {accel_label}")
    print("=" * 72)

    try:
        import snapml
        print(f"[+] Snap ML Version: {version('snapml')}")
    except ImportError:
        print("[!] Snap ML is not installed in the current environment.")
        print("    Install on LinuxONE via: python3 -m pip install --break-system-packages snapml")
        return None

    from sklearn.datasets import make_classification
    from sklearn.ensemble import RandomForestClassifier as SklearnRF
    from snapml import RandomForestClassifier as SnapRF

    num_threads = os.cpu_count() or 3
    print(f"[+] Worker threads: {num_threads}")
    print(f"[+] Synthetic dataset: {n_samples:,} samples, {n_features} features")
    X, y = make_classification(n_samples=n_samples, n_features=n_features, random_state=42)

    # 1. Scikit-Learn RF Training
    print("\n[*] Measuring Scikit-Learn RF training time...")
    t0 = time.perf_counter()
    sk_model = SklearnRF(n_estimators=n_estimators, random_state=42, n_jobs=num_threads).fit(X, y)
    t_sk = time.perf_counter() - t0
    print(f"    -> Scikit-Learn CPU Time: {t_sk:.3f}s")

    # 2. Snap ML RF Training
    snap_label = f"IBM Snap ML ({accel_label})"
    print(f"[*] Measuring {snap_label} training time...")
    t0 = time.perf_counter()
    snap_model = SnapRF(n_estimators=n_estimators, random_state=42, n_jobs=num_threads).fit(X, y)
    t_snap = time.perf_counter() - t0
    print(f"    -> Snap ML Execution Time: {t_snap:.3f}s")

    speedup = t_sk / max(t_snap, 1e-6)
    print("-" * 72)
    print(f"[>>>] Result: RF Training Speedup = {speedup:.2f}x faster with Snap ML")
    print("=" * 72)

    # 3. Real Risk Model Inference Benchmark: Snap ML vs XGBoost
    run_inference_benchmark(num_threads)
    return {"sklearn_time": t_sk, "snapml_time": t_snap, "speedup": speedup}


def run_inference_benchmark(num_threads: int):
    """Snap ML vs XGBoost inference benchmark on the real panel risk model dataset."""
    from src import config
    from src.data import db
    import xgboost as xgb

    model_path = config.DATA_DIR / "risk_model.json"
    if not model_path.exists() or not db.table_exists("tract_year"):
        print("[*] Inference benchmark skipped: risk_model.json or tract_year table not found.")
        return

    print("\n" + "=" * 72)
    print("  Benchmark: Risk Model Inference Latency (XGBoost vs Snap ML)")
    print("=" * 72)

    try:
        panel = db.read_table("tract_year")
        feats = config.ENV_FEATURES
        test = panel[panel.year.isin(config.TEST_YEARS)]
        if len(test) == 0:
            test = panel
        X_test = test[feats]

        # XGBoost inference
        xgb_model = xgb.XGBClassifier()
        xgb_model.load_model(str(model_path))

        # Warmup
        _ = xgb_model.predict_proba(X_test.iloc[:20])

        t0 = time.perf_counter()
        _ = xgb_model.predict_proba(X_test)
        t_xgb = time.perf_counter() - t0
        print(f"    -> XGBoost Inference Time ({len(X_test):,} rows): {t_xgb*1000:.2f} ms")

        # Snap ML inference
        try:
            from snapml import BoostingMachineClassifier
            train = panel[panel.year.isin(config.TRAIN_YEARS)]
            snap_bm = BoostingMachineClassifier(num_round=250, max_depth=3, learning_rate=0.05, n_jobs=num_threads)
            snap_bm.fit(train[feats], train.burned)

            # Warmup
            _ = snap_bm.predict_proba(X_test.iloc[:20])

            t0 = time.perf_counter()
            _ = snap_bm.predict_proba(X_test)
            t_snap = time.perf_counter() - t0
            print(f"    -> Snap ML BoostingMachine Inference Time ({len(X_test):,} rows): {t_snap*1000:.2f} ms")
            ratio = t_xgb / max(t_snap, 1e-6)
            print(f"    -> Inference Ratio: {ratio:.2f}x ({'faster' if ratio >= 1 else 'slower'})")
        except Exception as e:
            print(f"    -> Snap ML model comparison note: {e}")
    except Exception as e:
        print(f"    -> Inference benchmark note: {e}")
    print("=" * 72)


if __name__ == "__main__":
    run_snapml_benchmark()
