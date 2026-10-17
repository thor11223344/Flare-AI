"""Unit tests for Phase 3: IBM Z Telum Readiness, ONNX prediction equivalence,
Db2 bulk loader dry-run, and governance log extensions.
"""
import json
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
import xgboost as xgb
from src import config
from src.ibmz import scoring, db2_load, benchmark, governance


def test_onnx_export_and_prediction_match(pipeline):
    """Verify that ONNX model export matches XGBoost predictions within 1e-4 tolerance."""
    scoring._model = None  # Force reload from test data dir
    onnx_path = scoring.export_onnx()
    assert Path(onnx_path).exists()

    # Load original XGBoost model
    xgb_model = xgb.XGBClassifier()
    xgb_model.load_model(str(config.DATA_DIR / "risk_model.json"))

    # Generate test feature dataframe
    rng = np.random.default_rng(42)
    X_mat = rng.random((100, len(config.ENV_FEATURES))).astype(np.float32)
    X_df = pd.DataFrame(X_mat, columns=config.ENV_FEATURES)

    xgb_probs = xgb_model.predict_proba(X_df)[:, 1]
    onnx_probs = scoring.score_onnx(X_df, model_path=onnx_path)

    assert len(xgb_probs) == len(onnx_probs)
    max_diff = np.max(np.abs(xgb_probs - onnx_probs))
    assert max_diff < 1e-4, f"Prediction mismatch between XGBoost and ONNX: max_diff={max_diff:.6f}"


def test_db2_load_dry_run_and_ddl_parsing(pipeline):
    """Verify Db2 loader dry run parses DDL and generates parameterized insert SQL without credentials."""
    summary = db2_load.run_db2_load(dry_run=True, verbose=False)
    assert summary["dry_run"] is True
    assert summary["ddl_statements_count"] >= 4
    assert "tracts" in summary["tables_found"]
    assert "policies" in summary["tables_found"]

    sql = db2_load.generate_insert_sql("policies", ["policy_id", "tract_id", "premium"])
    assert "INSERT INTO WILDFIRE.POLICIES" in sql
    assert "VALUES (?, ?, ?)" in sql


def test_latency_benchmark_execution(pipeline):
    """Verify latency benchmark runs over synthetic policies and outputs p50/p99."""
    scoring._model = None
    res = benchmark.run_benchmark(n_policies=500, n_single_calls=50, seed=42)
    assert "single_row_benchmark" in res
    assert res["single_row_benchmark"]["latency_p50_ms"] > 0
    assert res["single_row_benchmark"]["latency_p99_ms"] >= res["single_row_benchmark"]["latency_p50_ms"]
    assert res["hardware_environment"]["is_telum"] is False
    assert "laptop CPU, not Telum" in res["hardware_environment"]["label"]
    assert "expected to be deployable on Telum" in res["deployment_assessment"]


def test_governance_log_contains_onnx_and_benchmark(pipeline):
    """Verify that watsonx governance factsheet includes ONNX model hash and Telum latency readiness."""
    m, a = pipeline
    log_path = governance.log_run(m, a)
    assert Path(log_path).exists()

    rec = json.loads(Path(log_path).read_text())
    assert "onnx_deployment" in rec["model"]
    assert rec["model"]["onnx_deployment"]["in_place_scoring_ready"] is True
    assert rec["model"]["onnx_deployment"]["onnx_model_hash"] is not None
    assert "ibmz_telum_readiness" in rec
