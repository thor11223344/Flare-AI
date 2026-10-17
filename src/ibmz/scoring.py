"""In-place renewal-time scoring endpoint (stub) + ONNX export path for Telum.

On IBM Z the same model is exported to ONNX and served through the Z Deep Learning Compiler /
ONNX Runtime so inference executes on the Telum on-chip AI accelerator next to the transaction.
Here: a local function plus an optional FastAPI-style handler with no extra dependencies.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import xgboost as xgb
from src import config
from src.data import db

_model = None


def _load():
    global _model
    if _model is None:
        _model = xgb.XGBClassifier()
        _model.load_model(str(config.DATA_DIR / "risk_model.json"))
    return _model


def score_tract_conditions(features: dict) -> dict:
    """Score one tract-year of environmental features. Rejects demographics outright."""
    bad = set(features) - set(config.ENV_FEATURES)
    if bad:
        raise ValueError(f"Only environmental features accepted; got extra: {sorted(bad)}")
    X = pd.DataFrame([features])[config.ENV_FEATURES]
    p = float(_load().predict_proba(X)[0, 1])
    return dict(burn_probability=p)


def renewal_lookup(tract_id: str) -> dict:
    """What the renewal system would call: precomputed tract risk read from Db2 / SQLite in place."""
    df = db.query("SELECT risk_score, risk_lo, risk_hi FROM risk_scores WHERE tract_id = ?" if config.DB_BACKEND == "sqlite"
                  else "SELECT RISK_SCORE, RISK_LO, RISK_HI FROM WILDFIRE.RISK_SCORES WHERE TRACT_ID = ?", params=[tract_id])
    return {} if df.empty else {k.lower(): float(v) for k, v in df.iloc[0].items()}


def handle_request(payload: dict) -> dict:
    """POST /score handler body. payload = {'tract_id': ...} or {'features': {...}}."""
    if "features" in payload:
        return score_tract_conditions(payload["features"])
    return renewal_lookup(payload["tract_id"])


def export_onnx(path=None) -> str:
    """Export to ONNX (uses onnxmltools & onnxruntime) for IBM Z Telum coprocessor deployment."""
    from onnxmltools import convert_xgboost
    from onnxmltools.convert.common.data_types import FloatTensorType
    model = _load()
    booster = model.get_booster()
    orig_names = booster.feature_names
    # onnxmltools requires booster feature names to follow 'f%d' pattern
    booster.feature_names = [f"f{i}" for i in range(len(config.ENV_FEATURES))]
    try:
        onx = convert_xgboost(
            booster,
            initial_types=[("input", FloatTensorType([None, len(config.ENV_FEATURES)]))]
        )
    finally:
        booster.feature_names = orig_names

    path = path or str(config.DATA_DIR / "risk_model.onnx")
    with open(path, "wb") as f:
        f.write(onx.SerializeToString())
    return path


def score_onnx(features_df: pd.DataFrame, model_path: str = None) -> np.ndarray:
    """Run inference using ONNX Runtime (simulating IBM Z Telum ONNX pipeline)."""
    import onnxruntime as ort
    path = model_path or str(config.DATA_DIR / "risk_model.onnx")
    if not Path(path).exists():
        export_onnx(path)
    sess = ort.InferenceSession(path)
    input_name = sess.get_inputs()[0].name
    X_val = features_df[config.ENV_FEATURES].values.astype(np.float32)
    raw = sess.run(None, {input_name: X_val})
    probs = raw[1]
    if isinstance(probs, list):
        return np.array([p[1] for p in probs])
    return probs[:, 1]

