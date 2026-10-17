"""Synthetic data generation (tracts, yearly fire outcomes, policies).

Everything here is SYNTHETIC. If real files are dropped into data/raw/ (see README) the tract
loader uses them; otherwise realistic placeholders are generated and flagged is_placeholder=1.

Planted bias: premiums and non-renewals include a hidden penalty that grows as tract income
falls. The audit module must recover it. Legitimate confounders (older homes, weaker mitigation
in poorer tracts) are also built in so controlling for them matters.
"""
import json
import hashlib
import numpy as np
import pandas as pd
from src import config
from src.data import db

# (county, lat, lon, spread_deg, veg_bias, share)
COUNTIES = [
    ("Los Angeles", 34.15, -118.25, 0.45, 0.10, 0.22), ("San Diego", 33.00, -117.05, 0.30, 0.10, 0.12),
    ("Riverside", 33.85, -116.50, 0.45, 0.05, 0.08), ("San Bernardino", 34.20, -117.20, 0.45, 0.05, 0.07),
    ("Ventura", 34.40, -119.10, 0.25, 0.15, 0.04), ("Santa Barbara", 34.60, -120.00, 0.25, 0.15, 0.03),
    ("Sonoma", 38.50, -122.80, 0.25, 0.20, 0.04), ("Napa", 38.50, -122.30, 0.15, 0.20, 0.02),
    ("Butte", 39.70, -121.60, 0.25, 0.25, 0.03), ("Shasta", 40.65, -122.10, 0.30, 0.25, 0.03),
    ("Alameda", 37.70, -122.10, 0.15, -0.05, 0.08), ("Santa Clara", 37.30, -121.90, 0.20, -0.05, 0.07),
    ("Sacramento", 38.55, -121.45, 0.25, -0.15, 0.06), ("Fresno", 36.75, -119.75, 0.40, -0.10, 0.05),
    ("El Dorado", 38.75, -120.60, 0.25, 0.20, 0.03), ("Kern", 35.40, -118.90, 0.50, -0.10, 0.03),
]


def _sigmoid(x):
    return 1 / (1 + np.exp(-x))


def make_tracts(rng: np.random.Generator) -> pd.DataFrame:
    n = config.N_TRACTS
    shares = np.array([c[5] for c in COUNTIES]); shares = shares / shares.sum()
    idx = rng.choice(len(COUNTIES), size=n, p=shares)
    rows = []
    for i, ci in enumerate(idx):
        name, lat, lon, spread, vb, _ = COUNTIES[ci]
        rows.append(dict(tract_id=f"06{ci:02d}{i:06d}", county=name,
                         lat=lat + rng.normal(0, spread / 2), lon=lon + rng.normal(0, spread / 2),
                         veg_bias=vb))
    t = pd.DataFrame(rows)
    # --- environmental features (what the risk model is allowed to see) ---
    t["vegetation"] = np.clip(0.5 + t.veg_bias + rng.normal(0, 0.2, n), 0, 1)
    t["slope"] = np.clip(rng.gamma(2.0, 6.0, n) * (0.6 + t.vegetation), 0, 45)
    t["elevation"] = np.clip(rng.gamma(2.5, 250, n), 0, 3000)
    t["wui_proximity"] = np.clip(rng.beta(2, 2, n) * (0.5 + t.vegetation), 0, 1)
    t["drought_base"] = np.clip(rng.normal(0.5, 0.15, n) + 0.1 * (t.lat < 35), 0, 1)
    t["wind_base"] = np.clip(rng.normal(8, 2.5, n) + 2 * (t.elevation < 600), 2, 25)
    # --- demographics (AUDIT ONLY; weakly correlated with risk, realistically messy) ---
    z = (-0.30 * (t.vegetation - 0.5) / 0.2 + rng.normal(0, 1, n))
    t["median_income"] = np.round(np.exp(11.1 + 0.55 * z) / 100) * 100          # ~ $65k median
    t["median_home_value"] = np.round(np.exp(13.0 + 0.45 * z + rng.normal(0, 0.25, n)) / 1000) * 1000
    t["pct_minority"] = np.clip(0.55 - 0.18 * z + rng.normal(0, 0.15, n), 0.02, 0.98)
    t["renter_share"] = np.clip(0.42 - 0.15 * z + rng.normal(0, 0.1, n), 0.02, 0.95)
    t["svi"] = np.clip(0.5 - 0.22 * z + rng.normal(0, 0.12, n), 0, 1)
    t["income_quintile"] = pd.qcut(t.median_income, 5, labels=[1, 2, 3, 4, 5]).astype(int)  # 1 = lowest
    t["is_placeholder"] = 1
    # true static burn logit (hidden ground truth used only to generate outcomes and policies)
    t["true_logit"] = (-3.9 + 2.6 * (t.vegetation - 0.5) + 0.045 * (t.slope - 12) + 1.6 * (t.wui_proximity - 0.4)
                       + 2.2 * (t.drought_base - 0.5) + 0.12 * (t.wind_base - 8) - 0.0003 * (t.elevation - 600))
    return t.drop(columns="veg_bias")


def load_real_tracts_if_present():
    p = config.DATA_DIR / "raw" / "tracts.csv"
    if p.exists():
        t = pd.read_csv(p)
        need = {"tract_id", "county", "lat", "lon", *config.ENV_FEATURES[:4], "drought_base", "wind_base",
                "median_income", "median_home_value", "pct_minority", "renter_share", "svi"}
        miss = need - set(t.columns)
        if miss:
            raise ValueError(f"data/raw/tracts.csv missing columns: {sorted(miss)}")
        t["income_quintile"] = pd.qcut(t.median_income, 5, labels=[1, 2, 3, 4, 5]).astype(int)
        if "is_placeholder" not in t.columns:
            t["is_placeholder"] = 0
        if "true_logit" not in t.columns or t["true_logit"].isna().any():
            t["true_logit"] = (-3.9 + 2.6 * (t.vegetation - 0.5) + 0.045 * (t.slope - 12) + 1.6 * (t.wui_proximity - 0.4)
                               + 2.2 * (t.drought_base - 0.5) + 0.12 * (t.wind_base - 8) - 0.0003 * (t.elevation - 600))
        return t
    return None


def make_panel(tracts: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Tract-year panel: yearly weather + whether a significant wildfire burned the tract."""
    years = config.YEARS
    n = len(tracts)
    out = []
    burned_hist = np.zeros((n, len(years)), dtype=int)
    drought_trend = np.linspace(-0.03, 0.06, len(years))            # drier over time
    for j, y in enumerate(years):
        drought = np.clip(tracts.drought_base.values + drought_trend[j] + rng.normal(0, 0.08, n), 0, 1)
        wind = np.clip(tracts.wind_base.values + rng.normal(0, 2.0, n), 1, 30)
        temp = rng.normal(0.4 + 0.05 * j, 0.5, n)
        prior5 = burned_hist[:, max(0, j - 5):j].sum(axis=1)
        logit = (tracts.true_logit.values + 2.2 * (drought - tracts.drought_base.values)
                 + 0.12 * (wind - tracts.wind_base.values) + 0.25 * temp - 0.2 * prior5)
        burned = rng.random(n) < _sigmoid(logit)
        burned_hist[:, j] = burned
        out.append(pd.DataFrame(dict(tract_id=tracts.tract_id.values, year=y, drought_index=drought,
                                     wind_speed=wind, temp_anomaly=temp, fires_prior5=prior5,
                                     burned=burned.astype(int))))
    panel = pd.concat(out, ignore_index=True)
    static = tracts[["tract_id", "vegetation", "slope", "elevation", "wui_proximity"]]
    return panel.merge(static, on="tract_id")


def make_policies(tracts: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Synthetic policies. Premium/non-renewal depend on TRUE risk + legit factors + planted penalty."""
    k = config.POLICIES_PER_TRACT
    t = tracts.reset_index(drop=True)
    n = len(t) * k
    ti = np.repeat(np.arange(len(t)), k)
    tl = t.true_logit.values[ti]
    risk_z = (tl - t.true_logit.mean()) / t.true_logit.std()
    q = t.income_quintile.values[ti]
    income_deficit = (5 - q) / 4.0                                    # 1 for lowest quintile, 0 for highest
    # legitimate confounders: poorer tracts have older homes & weaker mitigation
    home_age = np.clip(rng.normal(35 + 8 * income_deficit, 15, n), 1, 120)
    mitigation = np.clip(rng.beta(2.5, 2.5, n) - 0.12 * income_deficit + 0.04 * rng.normal(size=n), 0, 1)
    coverage = t.median_home_value.values[ti] * np.exp(rng.normal(0, 0.25, n))
    log_rate = (np.log(2.2) + 0.55 * risk_z + 0.004 * home_age - 0.35 * mitigation
                + config.INCOME_PENALTY_PREMIUM * income_deficit + rng.normal(0, 0.15, n))
    premium = coverage / 1000 * np.exp(log_rate)
    nr_logit = (-3.6 + 0.9 * risk_z + 0.012 * home_age - 0.9 * mitigation
                + config.INCOME_PENALTY_NONRENEWAL * income_deficit)
    non_renewal = rng.random(n) < _sigmoid(nr_logit)
    dn_logit = nr_logit - 0.4
    denial = rng.random(n) < _sigmoid(dn_logit)
    pol = pd.DataFrame(dict(policy_id=np.arange(n), tract_id=t.tract_id.values[ti], premium=premium.round(2),
                            coverage=coverage.round(0), home_age=home_age.round(1),
                            mitigation_score=mitigation.round(3), non_renewal_flag=non_renewal.astype(int),
                            denial_flag=denial.astype(int)))
    return pol


def data_hash(*dfs) -> str:
    h = hashlib.sha256()
    for d in dfs:
        h.update(pd.util.hash_pandas_object(d, index=False).values.tobytes())
    return h.hexdigest()[:16]


def run() -> dict:
    rng = np.random.default_rng(config.SEED)
    tracts = load_real_tracts_if_present()
    if tracts is None:
        tracts = make_tracts(rng)
        # Deterministically map synthetic tract IDs to real California GEOIDs & real centroids
        try:
            from src.data.geo import get_deterministic_mapping, load_real_tract_geometries
            mapping = get_deterministic_mapping(tracts["tract_id"].tolist(), seed=config.SEED)
            if mapping:
                tracts["real_geoid"] = tracts["tract_id"].map(mapping)
                geoms = load_real_tract_geometries()
                if geoms is not None and not geoms.empty:
                    c_map = geoms.set_index("real_geoid")[["real_lat", "real_lon"]]
                    tracts["lat"] = tracts["real_geoid"].map(c_map["real_lat"]).fillna(tracts["lat"])
                    tracts["lon"] = tracts["real_geoid"].map(c_map["real_lon"]).fillna(tracts["lon"])
                tracts["geometry_source"] = "cb_2022_06_tract_500k (sampled)"
        except Exception as e:
            print(f"[generate] Real geometry mapping fallback: {e}")
            tracts["geometry_source"] = "centroid_placeholder"
    panel = make_panel(tracts, rng)
    policies = make_policies(tracts, rng)
    db.write_table(tracts.drop(columns=["true_logit"]), "tracts")
    db.write_table(panel, "tract_year")
    db.write_table(policies, "policies")
    # ground truth kept separately; used ONLY for validation/tests, never by models or the app
    tracts[["tract_id", "true_logit"]].to_csv(config.DATA_DIR / "ground_truth.csv", index=False)
    params = dict(seed=config.SEED, n_tracts=len(tracts), n_policies=len(policies),
                  years=[config.YEARS[0], config.YEARS[-1]],
                  income_penalty_premium=config.INCOME_PENALTY_PREMIUM,
                  income_penalty_nonrenewal=config.INCOME_PENALTY_NONRENEWAL,
                  note=config.SYNTHETIC_NOTE, data_hash=data_hash(tracts.drop(columns=["true_logit"]), policies))
    (config.DATA_DIR / "params.json").write_text(json.dumps(params, indent=2))
    return params


if __name__ == "__main__":
    print(run())
