"""Wildfire risk model: environmental features ONLY, temporal validation, SHAP, uncertainty."""
import json
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.calibration import calibration_curve
from src import config
from src.data import db

PARAMS = dict(n_estimators=250, max_depth=3, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
              min_child_weight=5, reg_lambda=2.0, eval_metric="logloss", n_jobs=2, tree_method="hist")


def assert_no_leakage(features):
    bad = set(features) & set(config.FORBIDDEN_FEATURES)
    extra = set(features) - set(config.ENV_FEATURES)
    if bad or extra:
        raise ValueError(f"Risk model may only use environmental features. Offending: {sorted(bad | extra)}")


def _logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def train_and_score(save_plots=True) -> dict:
    feats = config.ENV_FEATURES
    assert_no_leakage(feats)
    panel = db.read_table("tract_year")
    tracts = db.read_table("tracts")
    train = panel[panel.year.isin(config.TRAIN_YEARS)]
    test = panel[panel.year.isin(config.TEST_YEARS)]   # LATER seasons: genuine temporal holdout

    model = xgb.XGBClassifier(**PARAMS, random_state=config.SEED)
    model.fit(train[feats], train.burned)
    p_test = model.predict_proba(test[feats])[:, 1]
    auc = roc_auc_score(test.burned, p_test)
    brier = brier_score_loss(test.burned, p_test)
    base_brier = brier_score_loss(test.burned, np.full(len(test), train.burned.mean()))
    frac_pos, mean_pred = calibration_curve(test.burned, p_test, n_bins=8, strategy="quantile")
    calib = [dict(mean_predicted=float(a), observed_rate=float(b)) for a, b in zip(mean_pred, frac_pos)]
    calib_err = float(np.mean(np.abs(frac_pos - mean_pred)))

    # tract-level risk score: mean predicted annual burn probability over all years' conditions
    full = panel.copy()
    full["p"] = model.predict_proba(full[feats])[:, 1]
    score = full.groupby("tract_id").p.mean().rename("risk_score")

    # uncertainty: bootstrap ensemble over TRACTS (resample tracts, refit, spread of tract scores)
    rng = np.random.default_rng(config.SEED)
    tract_ids = train.tract_id.unique()
    ens = []
    for b in range(8):
        samp = rng.choice(tract_ids, size=len(tract_ids), replace=True)
        w = pd.Series(samp).value_counts()
        tr = train.assign(w=train.tract_id.map(w).fillna(0))
        tr = tr[tr.w > 0]
        m = xgb.XGBClassifier(**PARAMS, random_state=config.SEED + b + 1)
        m.fit(tr[feats], tr.burned, sample_weight=tr.w)
        full[f"p{b}"] = m.predict_proba(full[feats])[:, 1]
        ens.append(full.groupby("tract_id")[f"p{b}"].mean())
    ens = pd.concat(ens, axis=1)
    unc = ens.std(axis=1).rename("risk_uncertainty")
    out = pd.concat([score, unc, ens.quantile(0.05, axis=1).rename("risk_lo"),
                     ens.quantile(0.95, axis=1).rename("risk_hi")], axis=1).reset_index()
    out["risk_percentile"] = out.risk_score.rank(pct=True)
    out["risk_logit_z"] = (_logit(out.risk_score) - _logit(out.risk_score).mean()) / _logit(out.risk_score).std()
    db.write_table(out, "risk_scores")

    # error rates by income group (fairness of the RISK model itself, test years)
    tq = tracts[["tract_id", "income_quintile"]]
    t2 = test.assign(p=p_test).merge(tq, on="tract_id")
    by_group = []
    for q, g in t2.groupby("income_quintile"):
        by_group.append(dict(income_quintile=int(q), auc=float(roc_auc_score(g.burned, g.p)),
                             brier=float(brier_score_loss(g.burned, g.p)),
                             mean_pred=float(g.p.mean()), observed=float(g.burned.mean())))

    # SHAP
    shap_imp = {}
    try:
        import shap
        sample = test.sample(min(2000, len(test)), random_state=config.SEED)[feats]
        sv = shap.TreeExplainer(model).shap_values(sample)
        shap_imp = dict(sorted(zip(feats, np.abs(sv).mean(axis=0).round(4).tolist()), key=lambda kv: -kv[1]))
        if save_plots:
            import matplotlib; matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            shap.summary_plot(sv, sample, show=False)
            plt.tight_layout(); plt.savefig(config.DATA_DIR / "shap_summary.png", dpi=120); plt.close()
    except Exception as e:  # SHAP is nice-to-have; never block the pipeline
        shap_imp = {"error": str(e)}

    model.save_model(str(config.DATA_DIR / "risk_model.json"))
    metrics = dict(model="xgboost", features=feats, train_years=[config.TRAIN_YEARS[0], config.TRAIN_YEARS[-1]],
                   test_years=[config.TEST_YEARS[0], config.TEST_YEARS[-1]], test_auc=float(auc),
                   test_brier=float(brier), baseline_brier=float(base_brier),
                   brier_skill=float(1 - brier / max(base_brier, 1e-9)), calibration_mae=calib_err, calibration=calib,
                   by_income_quintile=by_group, shap_importance=shap_imp)
    (config.DATA_DIR / "risk_metrics.json").write_text(json.dumps(metrics, indent=2))
    return metrics


if __name__ == "__main__":
    m = train_and_score()
    print({k: v for k, v in m.items() if k in ("test_auc", "brier_skill", "calibration_mae", "shap_importance")})
