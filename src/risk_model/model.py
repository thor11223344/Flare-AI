"""Wildfire risk model: environmental features ONLY, temporal validation, SHAP, bootstrap uncertainty."""
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score, brier_score_loss
from src import config as C

FEATURES = list(C.ENV_FEATURES)
PARAMS = dict(n_estimators=250, max_depth=3, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
              min_child_weight=5, reg_lambda=2.0, eval_metric="logloss", n_jobs=2)


def assert_no_demographics(cols):
    bad = [c for c in cols if any(f in c.lower() for f in C.FORBIDDEN_FRAGMENTS)]
    if bad:
        raise ValueError(f"Demographic columns not allowed in risk model: {bad}")


def build_panel(tracts, panel):
    p = panel.merge(tracts[["tract_id", "vegetation", "slope", "elevation"]], on="tract_id")
    return p[p["year"] >= C.MODEL_START_YEAR].reset_index(drop=True)


def _calibration(y, p, bins=10):
    df = pd.DataFrame({"y": y, "p": p})
    df["bin"] = pd.qcut(df["p"], bins, duplicates="drop")
    g = df.groupby("bin", observed=True).agg(pred=("p", "mean"), obs=("y", "mean"), n=("y", "size")).reset_index(drop=True)
    ece = float((g["n"] * (g["pred"] - g["obs"]).abs()).sum() / g["n"].sum())
    return g.round(5).to_dict("records"), ece


def _importance(model, X):
    try:
        import shap
        sv = shap.TreeExplainer(model).shap_values(X.sample(min(2000, len(X)), random_state=0))
        return dict(zip(FEATURES, np.abs(sv).mean(0).astype(float))), "shap"
    except Exception:
        return dict(zip(FEATURES, model.feature_importances_.astype(float))), "xgboost_gain"


def fit_and_score(tracts, panel, seed=None, n_boot=10):
    seed = C.SEED if seed is None else seed
    assert_no_demographics(FEATURES)
    data = build_panel(tracts, panel)
    train = data[data["year"] <= C.TRAIN_END_YEAR]
    test = data[data["year"] > C.TRAIN_END_YEAR].copy()
    Xtr, ytr, Xte, yte = train[FEATURES], train["fire"], test[FEATURES], test["fire"]

    model = xgb.XGBClassifier(**PARAMS, random_state=seed).fit(Xtr, ytr)
    p_te = model.predict_proba(Xte)[:, 1]
    cal, ece = _calibration(yte.to_numpy(), p_te)
    base_rate = float(ytr.mean())
    metrics = dict(
        train_years=f"{C.MODEL_START_YEAR}-{C.TRAIN_END_YEAR}", test_years=f"{C.TRAIN_END_YEAR + 1}-{C.YEARS[-1]}",
        n_train=int(len(train)), n_test=int(len(test)), test_positive_rate=float(yte.mean()),
        auc=float(roc_auc_score(yte, p_te)), brier=float(brier_score_loss(yte, p_te)),
        brier_baseline=float(brier_score_loss(yte, np.full(len(yte), base_rate))),
        ece=ece, calibration=cal, features=FEATURES,
    )

    # Error rates by income group (income used for AUDIT of the model only)
    inc = tracts.set_index("tract_id")["income_q"]
    test["income_q"] = test["tract_id"].map(inc).to_numpy()
    test["p"] = p_te
    grp = []
    for q, g in test.groupby("income_q"):
        auc = roc_auc_score(g["fire"], g["p"]) if g["fire"].nunique() > 1 else float("nan")
        grp.append(dict(income_q=int(q), auc=float(auc), brier=float(brier_score_loss(g["fire"], g["p"])),
                        mean_pred=float(g["p"].mean()), observed=float(g["fire"].mean()), n=int(len(g))))
    metrics["by_income_group"] = grp

    imp, method = _importance(model, Xte)
    metrics["importance"], metrics["importance_method"] = imp, method

    # Bootstrap ensemble -> per-tract risk and uncertainty on the held-out seasons
    rng = np.random.default_rng(seed)
    mats = []
    for _ in range(n_boot):
        ix = rng.integers(0, len(train), len(train))
        m = xgb.XGBClassifier(**PARAMS, random_state=int(rng.integers(1e9))).fit(Xtr.iloc[ix], ytr.iloc[ix])
        pt = pd.Series(m.predict_proba(Xte)[:, 1], index=test.index)
        mats.append(pt.groupby(test["tract_id"]).mean())
    M = pd.concat(mats, axis=1)
    scored = pd.DataFrame({"tract_id": M.index, "risk_prob": M.mean(1).to_numpy(), "risk_uncertainty": M.std(1).to_numpy()})
    scored["risk_score"] = (scored["risk_prob"].rank(pct=True) * 100).round(1)
    scored["risk_tier"] = pd.cut(scored["risk_score"], [0, 50, 80, 95, 100.01],
                                 labels=["Low", "Moderate", "High", "Extreme"], include_lowest=True).astype(str)
    return scored, metrics, model
