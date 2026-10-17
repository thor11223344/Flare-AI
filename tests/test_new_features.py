"""Unit tests for newly added capabilities:
1. Actuarial Counterfactual & Mitigation ROI Simulator (src/audit/counterfactual.py)
2. IBM watsonx.ai Granite Regulatory Memorandum Generator (src/explain/granite_memo.py)
3. 10-Year Climate Scenario Projections (src/risk_model/climate_scenarios.py)
"""
import pytest
import pandas as pd
from src.audit import counterfactual
from src.explain import granite_memo
from src.risk_model import climate_scenarios
from src.data import db


def test_counterfactual_mitigation_roi_simulator(pipeline):
    """Verify counterfactual fair rate calculation and mitigation savings."""
    tracts = db.read_table("tracts")
    sample_tid = tracts.tract_id.iloc[0]

    sim = counterfactual.simulate_property_quote(
        tract_id=sample_tid,
        home_age_years=40.0,
        mitigation_score=0.20,
        coverage_amount=600000.0,
        target_mitigation_score=0.80
    )

    assert sim["tract_id"] == sample_tid
    assert "pricing_counterfactual" in sim
    cf = sim["pricing_counterfactual"]
    assert cf["current_market_annual_premium"] > 0
    assert cf["actuarially_fair_annual_premium"] > 0

    # If tract is lower income (e.g. Q1), current premium >= fair premium
    if sim["income_quintile"] <= 2:
        assert cf["current_market_annual_premium"] >= cf["actuarially_fair_annual_premium"]

    assert "mitigation_roi" in sim
    roi = sim["mitigation_roi"]
    assert roi["annual_dollar_savings"] > 0
    assert roi["percent_savings"] > 0

    assert "non_renewal_risk" in sim
    assert 0 <= sim["non_renewal_risk"]["current_non_renewal_prob"] <= 1.0


def test_granite_regulatory_memo_generator(pipeline):
    """Verify watsonx.ai Granite regulatory memorandum synthesis."""
    tracts = db.read_table("tracts")
    sample_tid = tracts.tract_id.iloc[0]

    memo = granite_memo.generate_granite_regulatory_memo(tract_id=sample_tid)
    assert memo["tract_id"] == sample_tid
    assert "compliance_status" in memo
    assert memo["compliance_status"] in ["NON_COMPLIANT_FLAG", "COMPLIANT_BASELINE"]
    assert "memorandum_text" in memo
    text = memo["memorandum_text"]
    assert "CALIFORNIA DEPARTMENT OF INSURANCE" in text.upper()
    assert sample_tid in text
    assert "Proposition 103" in text or "1861.05" in text


def test_climate_scenario_projections(pipeline):
    """Verify 10-year climate scenario hazard modeling and availability cliff calculation."""
    tracts = db.read_table("tracts").head(50)  # test on subset for speed
    proj = climate_scenarios.project_tract_climate_scenarios(tracts)

    assert "risk_baseline" in proj.columns
    assert "risk_warming_1_5c" in proj.columns
    assert "risk_warming_2_0c" in proj.columns
    assert "cliff_warming_2_0c" in proj.columns

    # Warming scenarios should generally increase or maintain burn probability
    mean_base = proj["risk_baseline"].mean()
    mean_1_5 = proj["risk_warming_1_5c"].mean()
    mean_2_0 = proj["risk_warming_2_0c"].mean()
    assert mean_2_0 >= mean_1_5 >= (mean_base - 0.02)

    summary = climate_scenarios.summarize_climate_impact(proj)
    assert "baseline" in summary
    assert "warming_1_5c" in summary
    assert "warming_2_0c" in summary
    assert summary["warming_2_0c"]["total_cliff_tracts"] >= 0
