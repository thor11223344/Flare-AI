import numpy as np
import pytest
from src import config
from src.data import generate, db
from src.risk_model import train


def test_generator_schema_and_reproducible(pipeline):
    rng1, rng2 = np.random.default_rng(config.SEED), np.random.default_rng(config.SEED)
    a, b = generate.make_tracts(rng1), generate.make_tracts(rng2)
    assert a.equals(b)
    pol = db.read_table("policies")
    assert {"premium", "home_age", "mitigation_score", "non_renewal_flag", "denial_flag", "tract_id"} <= set(pol.columns)
    assert len(pol) == config.N_TRACTS * config.POLICIES_PER_TRACT and (pol.premium > 0).all()


def test_planted_penalty_is_present_in_data(pipeline):
    import pandas as pd
    t, p = db.read_table("tracts"), db.read_table("policies")
    d = p.merge(t[["tract_id", "income_quintile"]], on="tract_id")
    nr = d.groupby("income_quintile").non_renewal_flag.mean()
    assert nr.loc[1] > nr.loc[5]


def test_audit_recovers_planted_gap(pipeline):
    _, a = pipeline
    r = a["recovery"]
    assert r["premium_recovered"], r
    assert r["nonrenewal_recovered"], r
    # CI should cover the planted value
    q1 = a["premium_model"]["income_quintile_effects_log_points"][1]
    assert q1["lo"] <= config.INCOME_PENALTY_PREMIUM <= q1["hi"] or r["premium_abs_error"] < 0.03


def test_risk_model_uses_no_demographics(pipeline):
    m, _ = pipeline
    assert set(m["features"]) == set(config.ENV_FEATURES)
    assert not set(m["features"]) & set(config.FORBIDDEN_FEATURES)
    with pytest.raises(ValueError):
        train.assert_no_leakage(config.ENV_FEATURES + ["median_income"])


def test_temporal_split_has_no_overlap(pipeline):
    assert max(config.TRAIN_YEARS) < min(config.TEST_YEARS)


def test_risk_model_beats_baseline_on_future_years(pipeline):
    m, _ = pipeline
    assert m["test_auc"] > 0.65 and m["brier_skill"] > 0


def test_proxy_check_low(pipeline):
    _, a = pipeline
    assert a["proxy_check"]["env_to_income_cv_r2"] < 0.25


def test_scoring_endpoint_rejects_demographics(pipeline):
    from src.ibmz import scoring
    ok = scoring.score_tract_conditions({f: 0.5 for f in config.ENV_FEATURES})
    assert 0 <= ok["burn_probability"] <= 1
    with pytest.raises(ValueError):
        scoring.score_tract_conditions({**{f: 0.5 for f in config.ENV_FEATURES}, "median_income": 50000})
    tid = db.read_table("risk_scores").tract_id.iloc[0]
    assert "risk_score" in scoring.handle_request({"tract_id": tid})


def test_governance_log(pipeline):
    import json
    from src.ibmz import governance
    m, a = pipeline
    rec = json.loads(open(governance.log_run(m, a)).read())
    assert rec["model"]["demographics_used_as_inputs"] is False and "fairness" in rec
