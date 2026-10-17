"""Multi-Year Climate Scenario Projections (2025-2035).
Simulates wildfire hazard trajectories and flags Insurance Availability Cliffs
under +1.5°C and +2.0°C global warming scenarios for California census tracts.
"""
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from src import config
from src.data import db
from src.ibmz import scoring

SCENARIOS = {
    "baseline": {
        "name": "Current Baseline (2020-2024)",
        "temp_shift_c": 0.0,
        "drought_shift": 0.0,
        "wind_shift_mph": 0.0,
        "description": "Observed contemporary weather averages and fuel moisture levels."
    },
    "warming_1_5c": {
        "name": "+1.5°C Moderate Warming (2030 Projection)",
        "temp_shift_c": 1.2,
        "drought_shift": 0.08,
        "wind_shift_mph": 1.0,
        "description": "IPCC SSP2-4.5 intermediate pathway: prolonged drying season, +8% drought anomaly, +1.0 mph peak gusts."
    },
    "warming_2_0c": {
        "name": "+2.0°C Severe Warming (2035 Projection)",
        "temp_shift_c": 2.2,
        "drought_shift": 0.16,
        "wind_shift_mph": 2.5,
        "description": "IPCC SSP3-7.0 high-emission pathway: critical fuel aridity, +16% drought severity, intensified Diablo/Santa Ana winds."
    }
}


def project_tract_climate_scenarios(tract_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Evaluate wildfire burn probability across all census tracts under each climate scenario.
    Identifies 'Availability Cliff' tracts where burn probability exceeds 15% (underwriting exclusion threshold).
    """
    if tract_df is None:
        tract_df = db.read_table("tracts")

    t = tract_df.copy()
    n = len(t)
    feats = config.ENV_FEATURES

    # Ensure base features exist
    veg = t["vegetation"].values
    slope = t["slope"].values
    elev = t["elevation"].values
    wui = t["wui_proximity"].values
    drought_base = t["drought_base"].values
    wind_base = t["wind_base"].values

    results = t[["tract_id", "county", "lat", "lon", "income_quintile", "median_income"]].copy()

    for scen_key, scen in SCENARIOS.items():
        # Construct weather conditions adjusted for scenario
        drought = np.clip(drought_base + scen["drought_shift"], 0.0, 1.0)
        wind = np.clip(wind_base + scen["wind_shift_mph"], 2.0, 35.0)
        temp_anom = np.full(n, scen["temp_shift_c"], dtype=np.float32)
        fires_prior = np.clip(t.get("fires_prior5", np.zeros(n)) + (1 if scen_key != "baseline" else 0), 0, 5)

        X_scen = pd.DataFrame({
            "vegetation": veg,
            "slope": slope,
            "elevation": elev,
            "wui_proximity": wui,
            "drought_index": drought,
            "wind_speed": wind,
            "temp_anomaly": temp_anom,
            "fires_prior5": fires_prior
        })

        # Score via ONNX Runtime / scoring engine
        probs = scoring.score_onnx(X_scen)
        results[f"risk_{scen_key}"] = np.round(probs, 4)
        # Availability Cliff: Private insurers typically withdraw voluntary underwriting above 15% annual burn risk
        results[f"cliff_{scen_key}"] = (probs >= 0.15).astype(int)

    # Risk change deltas
    results["risk_delta_1_5c_pp"] = np.round((results["risk_warming_1_5c"] - results["risk_baseline"]) * 100.0, 2)
    results["risk_delta_2_0c_pp"] = np.round((results["risk_warming_2_0c"] - results["risk_baseline"]) * 100.0, 2)
    results["enters_cliff_under_2c"] = ((results["cliff_baseline"] == 0) & (results["cliff_warming_2_0c"] == 1)).astype(int)

    return results


def summarize_climate_impact(projected_df: pd.DataFrame) -> Dict[str, Any]:
    """Summarize climate impacts across income quintiles, identifying disproportionate cliff exposure."""
    summary: Dict[str, Any] = {}
    scenarios_dict: Dict[str, Any] = {}
    for scen_key, scen in SCENARIOS.items():
        avg_risk = float(projected_df[f"risk_{scen_key}"].mean())
        cliff_count = int(projected_df[f"cliff_{scen_key}"].sum())
        cliff_pct = float((cliff_count / len(projected_df)) * 100.0)

        # Breakdown by income quintile
        cliff_by_q = projected_df.groupby("income_quintile")[f"cliff_{scen_key}"].mean().to_dict()
        scen_info = {
            "name": scen["name"],
            "label": scen["name"],
            "avg_statewide_burn_prob": round(avg_risk, 4),
            "avg_burn_prob": round(avg_risk, 4),
            "total_cliff_tracts": cliff_count,
            "availability_cliff_tracts": cliff_count,
            "pct_tracts_in_cliff": round(cliff_pct, 1),
            "cliff_share_pct": round(cliff_pct, 1),
            "cliff_rate_by_income_quintile": {int(k): round(float(v) * 100, 1) for k, v in cliff_by_q.items()},
        }
        summary[scen_key] = scen_info
        scenarios_dict[scen_key] = scen_info

    summary["scenarios"] = scenarios_dict
    return summary
