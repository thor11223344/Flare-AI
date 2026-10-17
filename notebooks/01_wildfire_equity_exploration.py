"""
Wildfire Equity Map - Exploratory Analysis Script
IBM Z Datathon · Wildcard Track
Inspects data distributions, runs econometric regressions, and outputs summary tables.
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np

def main():
    print("=" * 60)
    print("WILDFIRE EQUITY MAP: EXPLORATORY DATA & AUDIT INSPECTOR")
    print("=" * 60)

    data_dir = Path("data")
    tracts = pd.read_csv(data_dir / "processed" / "tracts_with_risk.csv")
    with open(data_dir / "audit_results.json") as f:
        audit = json.load(f)

    print(f"\nLoaded {len(tracts):,} California Census Tracts across {tracts['county'].nunique()} Counties")
    print(f"Mean Predicted Risk Score: {tracts['predicted_risk_score'].mean():.1%}")
    print(f"Mean Annual Premium:       ${tracts['mean_premium'].mean():,.2f}")
    print(f"Mean Non-Renewal Rate:     {tracts['non_renewal_rate'].mean():.1%}")

    print("\n--- QUINTILE AGGREGATES & FAIRNESS AUDIT ---")
    q_summary = pd.DataFrame(audit["fairness_metrics"]["quintile_summary"])
    cols = ["income_quintile", "total_policies", "mean_premium", "mean_predicted_risk", "non_renewal_rate", "disparate_impact_ratio", "violates_80pct_rule"]
    print(q_summary[cols].to_string(index=False))

    print("\n--- GROUND TRUTH RECOVERY CHECK ---")
    rec = audit["recovery_check"]
    print(f"Planted Income Penalty:   {rec['planted_penalty_coef']}")
    print(f"Recovered OLS Penalty:   {rec['recovered_penalty_coef']} (95% CI: {rec['recovered_penalty_ci_95']})")
    print(f"Absolute Recovery Error: {rec['absolute_error']}")
    print(f"Recovery Verified:       {rec['penalty_recovered_successfully']}")

    print("\n--- UNEXPLAINED Q1 VS Q5 EQUITY GAP ---")
    print(f"Unexplained Premium Surcharge in Quintile 1: +{audit['ols_premium_regression']['unexplained_gap_q1_vs_q5_pct']:.2f}%")
    print(f"Non-Renewal Odds Ratio per Quintile Drop:   {audit['logistic_non_renewal']['odds_ratio_per_quintile_drop']:.3f}x")

if __name__ == "__main__":
    main()
