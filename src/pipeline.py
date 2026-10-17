"""Pipeline steps: data -> risk -> audit -> explain -> ibmz. Each step reads/writes through the DB layer."""
import json
import time
import pandas as pd
from src import config as C
from src.db import get_db
from src.data.generate import generate
from src.risk_model.model import fit_and_score
from src.audit.audit import run_audit, proxy_check
from src.explain.explainer import build_all
from src.ibmz import scoring, governance


def _save_json(obj, name):
    (C.DATA / name).write_text(json.dumps(obj, indent=2, default=str))


def step_data():
    db = get_db()
    tracts, panel, policies, params = generate()
    db.write(tracts, "tracts"); db.write(panel, "tract_year"); db.write(policies, "policies")
    db.index("policies", "tract_id")
    _save_json(params, "params.json")
    return f"{len(tracts)} tracts, {len(policies):,} synthetic policies, seed={params['seed']}"


def step_risk():
    db = get_db()
    tracts, panel = db.read("SELECT * FROM tracts"), db.read("SELECT * FROM tract_year")
    scored, metrics, model = fit_and_score(tracts, panel)
    db.write(scored, "tract_scores")
    onnx = scoring.save_model(model)
    metrics["onnx_export"] = onnx
    _save_json(metrics, "risk_metrics.json")
    return f"AUC={metrics['auc']:.3f} Brier={metrics['brier']:.4f} (baseline {metrics['brier_baseline']:.4f}) ECE={metrics['ece']:.4f}; ONNX={'yes' if onnx else 'skipped'}"


def step_audit():
    db = get_db()
    tracts, panel = db.read("SELECT * FROM tracts"), db.read("SELECT * FROM tract_year")
    scored, policies = db.read("SELECT * FROM tract_scores"), db.read("SELECT * FROM policies")
    params = json.loads((C.DATA / "params.json").read_text())
    res, tg = run_audit(tracts, scored, policies, params)
    res["proxy"] = proxy_check(tracts, panel, scored)
    res["planted_params"] = params
    db.write(tg, "tract_gaps")
    _save_json(res, "audit_results.json")
    q1 = res["outcomes"]["premium"]["rows"][0]
    return (f"Q1 premium gap {q1['coef']:.3f} (planted {q1['planted']:.3f}, CI {q1['ci_low']:.3f}..{q1['ci_high']:.3f}); "
            f"recovered {res['recovery']['n_recovered']}/{res['recovery']['n_total']}")


def step_explain():
    db = get_db()
    df = (db.read("SELECT * FROM tracts").merge(db.read("SELECT * FROM tract_scores"), on="tract_id")
          .merge(db.read("SELECT * FROM tract_gaps"), on="tract_id"))
    ex = build_all(df)
    db.write(ex, "tract_explainers")
    return f"{len(ex)} explainers"


def step_ibmz():
    db = get_db()
    tracts, policies = db.read("SELECT * FROM tracts"), db.read("SELECT * FROM policies")
    params = json.loads((C.DATA / "params.json").read_text())
    rm = json.loads((C.DATA / "risk_metrics.json").read_text())
    au = json.loads((C.DATA / "audit_results.json").read_text())
    path, _ = governance.log_run(tracts, policies, params, rm, au, db.name)
    demo = scoring.score_renewal(dict(vegetation=0.7, slope=0.5, elevation=0.5, drought=0.7, wind=0.6, fire_history=1))
    return f"governance log {path.name}; demo score {demo['annual_burn_probability']:.1%} in {demo['latency_ms']} ms"


STEPS = [("data", step_data), ("risk", step_risk), ("audit", step_audit), ("explain", step_explain), ("ibmz", step_ibmz)]


def run_all(only=None):
    for name, fn in STEPS:
        if only and name not in only:
            continue
        t = time.time()
        print(f"[{name}] running...", flush=True)
        msg = fn()
        print(f"[{name}] done in {time.time() - t:.1f}s: {msg}", flush=True)
