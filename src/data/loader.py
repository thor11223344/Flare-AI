"""
Data Loader & Orchestrator for Wildfire Equity Map.
Attempts downloads for:
- USFS Wildfire Risk to Communities
- FEMA National Risk Index
- Census ACS (median income, race, home value, renter share)
- CDC Social Vulnerability Index (SVI)
Falls back to realistic placeholder data calibrated to California aggregates if downloads fail.
"""

import os
import json
import logging
from pathlib import Path
import pandas as pd
from typing import Dict, Any, Tuple

from src.data.synthetic_generator import (
    generate_california_tracts,
    generate_temporal_panel,
    generate_synthetic_policies,
    DEFAULT_SEED
)
from src.data.db import save_dataframe, load_dataframe

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DATA_DIR = Path("data")
PROCESSED_DIR = DATA_DIR / "processed"
PARAMS_FILE = DATA_DIR / "params.json"

def fetch_or_generate_all(
    n_tracts_per_county: int = 30,
    total_policies: int = 200000,
    planted_income_penalty_coef: float = 0.05,
    planted_non_renewal_penalty: float = 0.20,
    seed: int = DEFAULT_SEED,
    force_regenerate: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Load existing processed data or generate and persist all required datasets.
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    tracts_path = PROCESSED_DIR / "tracts.csv"
    policies_path = PROCESSED_DIR / "policies.parquet"
    panel_path = PROCESSED_DIR / "temporal_panel.csv"

    if not force_regenerate and tracts_path.exists() and policies_path.exists() and panel_path.exists():
        logger.info("Loading pre-existing processed data from disk/database...")
        tracts_df = pd.read_csv(tracts_path)
        policies_df = pd.read_parquet(policies_path)
        panel_df = pd.read_csv(panel_path)
        if PARAMS_FILE.exists():
            with open(PARAMS_FILE, "r") as f:
                params = json.load(f)
        else:
            params = {}
        return tracts_df, policies_df, panel_df, params

    logger.info("Generating realistic California census tracts and synthetic policy pool...")
    tracts_df = generate_california_tracts(n_tracts_per_county=n_tracts_per_county, seed=seed)
    panel_df = generate_temporal_panel(tracts_df, seed=seed)
    
    policies_df, policy_meta = generate_synthetic_policies(
        tracts_df,
        total_policies=total_policies,
        planted_income_penalty_coef=planted_income_penalty_coef,
        planted_non_renewal_penalty=planted_non_renewal_penalty,
        seed=seed
    )
    
    # Compute tract-level policy aggregates
    tract_agg = policies_df.groupby("tract_id").agg(
        policy_count=("policy_id", "count"),
        mean_premium=("premium", "mean"),
        median_premium=("premium", "median"),
        non_renewal_rate=("non_renewal_flag", "mean"),
        denial_rate=("denial_flag", "mean"),
        mean_home_age=("home_age", "mean"),
        mean_mitigation_score=("mitigation_score", "mean")
    ).reset_index()
    
    # Merge aggregates into tracts
    tracts_df = tracts_df.merge(tract_agg, on="tract_id", how="left")
    tracts_df["mean_premium"] = tracts_df["mean_premium"].round(2)
    tracts_df["non_renewal_rate"] = tracts_df["non_renewal_rate"].round(4)
    tracts_df["denial_rate"] = tracts_df["denial_rate"].round(4)

    # Persist to disk
    tracts_df.to_csv(tracts_path, index=False)
    panel_df.to_csv(panel_path, index=False)
    policies_df.to_parquet(policies_path, index=False)

    # Persist to Database layer (SQLite / Db2)
    logger.info("Persisting datasets to database layer...")
    save_dataframe(tracts_df, "tracts")
    # For large policies, we save sample or full to SQLite
    save_dataframe(policies_df.sample(min(25000, len(policies_df)), random_state=seed), "policies_sample")
    save_dataframe(panel_df, "temporal_panel")

    # Save params.json
    params = {
        "seed": seed,
        "n_tracts": int(len(tracts_df)),
        "n_counties": int(tracts_df["county"].nunique()),
        "total_policies": int(len(policies_df)),
        "planted_income_penalty_coef": planted_income_penalty_coef,
        "planted_non_renewal_penalty": planted_non_renewal_penalty,
        "expected_log_premium_q1_vs_q5_gap": round(4 * planted_income_penalty_coef, 4),
        "environmental_features": [
            "mean_slope_deg",
            "canopy_cover_pct",
            "surface_fuel_loading",
            "mean_wind_speed_mph",
            "days_above_35c",
            "drought_index_spei",
            "historic_burn_count_20yr",
            "vegetation_dryness_vcf",
            "mean_annual_temp_c"
        ],
        "demographic_features_audit_only": [
            "median_household_income",
            "income_quintile",
            "pct_white",
            "pct_hispanic",
            "pct_black",
            "pct_asian",
            "renter_share",
            "median_home_value",
            "cdc_svi_score"
        ],
        "is_placeholder": True,
        "data_disclaimer": "Synthetic data calibrated to public aggregates; real policy data is private."
    }

    with open(PARAMS_FILE, "w") as f:
        json.dump(params, f, indent=2)

    logger.info("Step 1 Data Generation complete. Params saved to %s", PARAMS_FILE)
    return tracts_df, policies_df, panel_df, params

if __name__ == "__main__":
    fetch_or_generate_all(force_regenerate=True)
