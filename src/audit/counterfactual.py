"""Actuarial Counterfactual & Property Mitigation ROI Simulator.
Calculates what a property should pay under an actuarially fair rate (eliminating
unexplained demographic penalties) and computes annual premium savings from certified mitigation.
"""
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
from src import config
from src.data import db


def simulate_property_quote(
    tract_id: str,
    home_age_years: float = 35.0,
    mitigation_score: float = 0.30,
    coverage_amount: float = 500000.0,
    target_mitigation_score: Optional[float] = 0.85,
    db_conn=None,
    **kwargs
) -> Dict[str, Any]:
    """Calculate market premium vs actuarially fair counterfactual rate,
    and estimate return-on-investment (ROI) from certified property hardening.
    """
    if "home_age" in kwargs:
        home_age_years = kwargs["home_age"]
    if "existing_mitigation" in kwargs:
        mitigation_score = kwargs["existing_mitigation"]
    if "hardened_mitigation" in kwargs:
        target_mitigation_score = kwargs["hardened_mitigation"]

    tracts = db.read_table("tracts")
    risk_scores = db.read_table("risk_scores")
    audit_table = db.read_table("tract_audit")

    if isinstance(tract_id, (dict, pd.Series)):
        tract_id = tract_id.get("tract_id", "")

    tract_id_str = str(tract_id)
    tracts["tid_str"] = tracts["tract_id"].astype(str)
    risk_scores["tid_str"] = risk_scores["tract_id"].astype(str)
    audit_table["tid_str"] = audit_table["tract_id"].astype(str)

    t_match = tracts[tracts.tid_str == tract_id_str]
    if len(t_match) == 0 and tract_id_str.isdigit():
        t_match = tracts[tracts.tract_id == int(tract_id_str)]

    if len(t_match) == 0:
        raise ValueError(f"Tract ID {tract_id} not found in database.")

    t_row = t_match.iloc[0]
    real_tid = t_row["tract_id"]
    r_row = risk_scores[risk_scores.tract_id == real_tid].iloc[0]
    a_row = audit_table[audit_table.tract_id == real_tid].iloc[0]

    risk_score = float(r_row["risk_score"])
    income_quintile = int(t_row["income_quintile"])
    county = str(t_row["county"])
    median_income = float(t_row.get("median_income", 65000))

    # Standardize risk logit based on risk_scores distribution
    p_clip = np.clip(risk_score, 1e-4, 1.0 - 1e-4)
    logit_p = np.log(p_clip / (1.0 - p_clip))
    all_scores = risk_scores["risk_score"].clip(1e-4, 1.0 - 1e-4)
    all_logits = np.log(all_scores / (1.0 - all_scores))
    mean_logit = float(all_logits.mean())
    std_logit = float(max(all_logits.std(), 1e-4))
    risk_z = (logit_p - mean_logit) / std_logit

    log_cov = np.log(max(coverage_amount / 100000.0, 0.1))
    
    # Income penalty log points (Quintile 5 = 0, Quintile 1 = ~0.160 log points)
    penalty_log = (5 - income_quintile) * (config.INCOME_PENALTY_PREMIUM / 4.0)

    # 1. Current Market Premium (includes the unexplained income penalty)
    current_log_prem = (
        7.15 + 0.38 * risk_z + 0.0035 * (home_age_years - 30) - 0.28 * mitigation_score + 0.15 * log_cov + penalty_log
    )
    current_premium = float(np.exp(current_log_prem))
    current_rate_per_1000 = float((current_premium / coverage_amount) * 1000.0)

    # 2. Actuarially Fair Premium Counterfactual (penalty_log = 0: treated as Quintile 5 reference)
    fair_log_prem = (
        7.15 + 0.38 * risk_z + 0.0035 * (home_age_years - 30) - 0.28 * mitigation_score + 0.15 * log_cov + 0.0
    )
    fair_premium = float(np.exp(fair_log_prem))
    fair_rate_per_1000 = float((fair_premium / coverage_amount) * 1000.0)
    unexplained_annual_overcharge = float(max(current_premium - fair_premium, 0.0))

    # 3. Mitigation Hardening Simulation (e.g. State Grant: Class A Roof, Ember Vents, 100ft Defensible Space)
    mitigated_premium = None
    annual_mitigation_savings = None
    if target_mitigation_score is not None:
        mit_log_prem = (
            7.15 + 0.38 * risk_z + 0.0035 * (home_age_years - 30) - 0.28 * target_mitigation_score + 0.15 * log_cov + penalty_log
        )
        mitigated_premium = float(np.exp(mit_log_prem))
        annual_mitigation_savings = float(max(current_premium - mitigated_premium, 0.0))

    # 4. Non-renewal probability estimate
    # Non-renewal logit: -3.2 + 0.65 * risk_z + 0.008 * (age - 30) - 0.40 * mitigation + income_deficit * 0.50
    nr_logit = -3.2 + 0.65 * risk_z + 0.008 * (home_age_years - 30) - 0.40 * mitigation_score + (5 - income_quintile) * 0.125
    current_nr_prob = float(1.0 / (1.0 + np.exp(-nr_logit)))

    fair_nr_logit = -3.2 + 0.65 * risk_z + 0.008 * (home_age_years - 30) - 0.40 * mitigation_score + 0.0
    fair_nr_prob = float(1.0 / (1.0 + np.exp(-fair_nr_logit)))

    savings_dol = round(annual_mitigation_savings, 2) if annual_mitigation_savings else 0.0
    savings_pct = round((annual_mitigation_savings / current_premium) * 100, 1) if annual_mitigation_savings else 0.0
    five_yr = round(annual_mitigation_savings * 5, 2) if annual_mitigation_savings else 0.0

    return {
        "tract_id": tract_id,
        "county": county,
        "income_quintile": income_quintile,
        "median_income": median_income,
        "physical_burn_probability": risk_score,
        "property_inputs": {
            "home_age_years": home_age_years,
            "mitigation_score": mitigation_score,
            "coverage_amount": coverage_amount,
            "target_mitigation_score": target_mitigation_score,
        },
        "pricing_counterfactual": {
            "current_market_annual_premium": round(current_premium, 2),
            "current_rate_per_1000": round(current_rate_per_1000, 2),
            "actuarially_fair_annual_premium": round(fair_premium, 2),
            "fair_rate_per_1000": round(fair_rate_per_1000, 2),
            "unexplained_equity_surcharge_dollars": round(unexplained_annual_overcharge, 2),
            "unexplained_equity_surcharge_pct": round(((current_premium / fair_premium) - 1.0) * 100, 1),
        },
        "market_quote": {
            "annual_premium": round(current_premium, 2),
            "rate_per_1000": round(current_rate_per_1000, 2),
        },
        "counterfactual_quote": {
            "fair_annual_premium": round(fair_premium, 2),
            "fair_rate_per_1000": round(fair_rate_per_1000, 2),
        },
        "disparity_breakdown": {
            "unexplained_surcharge_dollars": round(unexplained_annual_overcharge, 2),
            "unexplained_surcharge_pct": round(((current_premium / fair_premium) - 1.0) * 100, 1),
        },
        "mitigation_roi": {
            "mitigated_annual_premium": round(mitigated_premium, 2) if mitigated_premium else None,
            "annual_dollar_savings": savings_dol,
            "annual_savings_dollars": savings_dol,
            "percent_savings": savings_pct,
            "savings_pct": savings_pct,
            "5yr_cumulative_savings": five_yr,
            "five_year_cumulative_savings": five_yr,
        },
        "non_renewal_risk": {
            "current_non_renewal_prob": round(current_nr_prob, 3),
            "fair_non_renewal_prob": round(fair_nr_prob, 3),
            "excess_non_renewal_risk_pp": round((current_nr_prob - fair_nr_prob) * 100, 1),
        }
    }
