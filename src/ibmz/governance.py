"""watsonx.governance-style run log: model version, data hash, fairness metrics, timestamp."""
import json
import hashlib
from datetime import datetime, timezone
from src import config


def log_run(risk_metrics: dict, audit: dict) -> str:
    params = json.loads((config.DATA_DIR / "params.json").read_text())
    model_path = config.DATA_DIR / "risk_model.json"
    model_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()[:16] if model_path.exists() else None

    # ONNX model export & hash for IBM Z Telum coprocessor deployment
    onnx_path = config.DATA_DIR / "risk_model.onnx"
    if not onnx_path.exists() and model_path.exists():
        try:
            from src.ibmz import scoring
            scoring.export_onnx(str(onnx_path))
        except Exception as e:
            print(f"[governance] Warning: ONNX auto-export skipped ({e})")

    onnx_hash = hashlib.sha256(onnx_path.read_bytes()).hexdigest()[:16] if onnx_path.exists() else None

    # Load latency benchmark result if available
    benchmark_path = config.DATA_DIR / "latency_benchmark.json"
    benchmark_data = None
    if benchmark_path.exists():
        try:
            benchmark_data = json.loads(benchmark_path.read_text())
        except Exception:
            benchmark_data = None

    ts = datetime.now(timezone.utc)
    rec = dict(
        run_id=ts.strftime("%Y%m%dT%H%M%SZ"), timestamp_utc=ts.isoformat(),
        model=dict(name="wildfire-risk-xgb", version=model_hash, features=risk_metrics["features"],
                   demographics_used_as_inputs=False, train_years=risk_metrics["train_years"],
                   test_years=risk_metrics["test_years"],
                   onnx_deployment=dict(onnx_model_hash=onnx_hash, target_coprocessor="IBM Telum (z16)",
                                        format="ONNX", in_place_scoring_ready=onnx_hash is not None)),
        data=dict(hash=params["data_hash"], seed=params["seed"], n_policies=params["n_policies"],
                  synthetic=True),
        performance=dict(test_auc=risk_metrics["test_auc"], brier_skill=risk_metrics["brier_skill"],
                         calibration_mae=risk_metrics["calibration_mae"]),
        ibmz_telum_readiness=dict(
            latency_benchmark=benchmark_data,
            hardware_environment="laptop CPU, not Telum",
            deployment_assessment="expected to be deployable on Telum via ONNX/IBM Z Deep Learning Compiler; not tested on Telum",
            hardware_note="Ran on laptop CPU, not Telum. Results do not prove Telum performance. Expected to be deployable on Telum via ONNX/IBM Z Deep Learning Compiler; not tested on Telum."
        ),
        fairness=dict(
            disparate_impact_ratio_renewal=audit["fairness"]["disparate_impact_ratio_renewal"],
            nonrenewal_rate_ratio_q1_vs_q5=audit["fairness"]["nonrenewal_rate_ratio_q1_vs_q5"],
            unexplained_premium_gap_q1_log=audit["premium_model"]["income_quintile_effects_log_points"][1]["coef"],
            unexplained_nonrenewal_gap_q1_logodds=audit["nonrenewal_model"]["income_quintile_effects_logodds"][1]["coef"],
            proxy_check_r2=audit["proxy_check"]["env_to_income_cv_r2"],
            risk_model_auc_by_income_quintile={str(d["income_quintile"]): d["auc"] for d in risk_metrics["by_income_quintile"]}),
        status="REVIEW_REQUIRED" if audit["fairness"]["nonrenewal_rate_ratio_q1_vs_q5"] > 1.25 else "PASS",
        note="watsonx.governance factsheet log. Tracks model provenance, cryptographic hashes, fairness gates, and Telum deployment readiness.")
    d = config.DATA_DIR / "governance_logs"
    d.mkdir(exist_ok=True)
    p = d / f"run_{rec['run_id']}.json"
    p.write_text(json.dumps(rec, indent=2))
    return str(p)
