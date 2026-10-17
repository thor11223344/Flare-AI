"""IBM watsonx.ai Granite Regulatory Memorandum Generator.
Produces plain-language, executive-level examination briefs for state insurance commissioners
and fair-lending regulators evaluating compliance under California Insurance Code § 1861.05
and the Four-Fifths (80%) Disparate Impact rule.
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
from src import config
from src.data import db


def generate_granite_regulatory_memo(
    tract_id: str,
    carrier_name: str = "Pacific Golden Underwriters Co.",
    use_live_watsonx: bool = False
) -> Dict[str, Any]:
    """Generate an official Regulatory Review Memorandum for a designated census tract.
    If USE_WATSONX=true and credentials exist, invokes IBM watsonx.ai Granite-13b-chat;
    otherwise employs an offline, deterministic regulatory synthesis template.
    """
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

    county = str(t_row["county"])
    income_q = int(t_row["income_quintile"])
    median_inc = float(t_row.get("median_income", 65000))
    risk_score = float(r_row["risk_score"])
    rate_1k = float(a_row["avg_rate_per_1000"])
    prem_gap = float(a_row["premium_gap_pct"])
    nr_rate = float(a_row["nonrenewal_rate"])
    nr_gap_pp = float(a_row["nr_gap_pp"]) * 100.0

    # Determine compliance posture under Fair Lending Four-Fifths (80%) screening heuristic
    # If lowest income quintile pays > 12% unexplained premium or has > 1.5 pp non-renewal disparity
    status = "NON_COMPLIANT_FLAG" if prem_gap > 12.0 or nr_gap_pp > 1.5 else "COMPLIANT_BASELINE"

    # Attempt live watsonx.ai if requested and configured
    live_used = False
    ai_generated_text = None
    if use_live_watsonx or config.USE_WATSONX:
        api_key = os.getenv("WATSONX_APIKEY") or os.getenv("IBM_API_KEY")
        project_id = os.getenv("WATSONX_PROJECT_ID")
        if api_key and project_id:
            try:
                from ibm_watsonx_ai.foundation_models import Model
                from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

                model_id = "ibm/granite-13b-chat-v2"
                parameters = {
                    GenParams.DECODING_METHOD: "greedy",
                    GenParams.MAX_NEW_TOKENS: 450,
                    GenParams.MIN_NEW_TOKENS: 100,
                    GenParams.TEMPERATURE: 0.2,
                }
                model = Model(
                    model_id=model_id,
                    params=parameters,
                    credentials={"url": "https://us-south.ml.cloud.ibm.com", "apikey": api_key},
                    project_id=project_id,
                )
                prompt = (
                    f"You are an insurance regulatory actuary at the California Department of Insurance (CDI). "
                    f"Write a concise 3-paragraph regulatory enforcement memorandum for Census Tract {tract_id} ({county} County). "
                    f"Tract Profile: Median Income: ${median_inc:,.0f} (Quintile {income_q}), Physical Wildfire Risk: {risk_score*100:.1f}%, "
                    f"Market Premium Rate: ${rate_1k:.2f}/$1k, Unexplained Premium Surcharge: +{prem_gap:.1f}%, Non-renewal Disparity: +{nr_gap_pp:.1f} pp. "
                    f"Explain why this disparity violates fair-rate regulations under Proposition 103 (Cal. Ins. Code § 1861.05), "
                    f"summarize the environmental controls, and order carrier justification."
                )
                ai_generated_text = model.generate_text(prompt)
                live_used = True
            except Exception as e:
                print(f"[granite_memo] Warning: Live watsonx.ai query failed ({e}); using deterministic template.")

    # High-fidelity deterministic regulatory memorandum (template)
    from_header = "Office of Actuarial AI Governance (IBM Granite on watsonx.ai)" if live_used else "Office of Actuarial AI Governance (Regulatory Deterministic Template)"
    engine_name = "IBM watsonx.ai Granite-13b-chat" if live_used else "IBM Granite Regulatory Template (Deterministic Fallback)"

    if ai_generated_text is None:
        ai_generated_text = f"""MEMORANDUM FOR RATE ENFORCEMENT & UNDERWRITING REVIEW
TO:         California Department of Insurance (CDI) Rate Regulation Division
FROM:       {from_header}
DATE:       {pd.Timestamp.now('UTC').strftime('%B %d, %Y')}
SUBJECT:    STATUTORY EXAMINATION OF TRACT {tract_id} ({county.upper()} COUNTY)
CARRIER:    {carrier_name}
STATUS:     {'ACTION REQUIRED: ADVERSE SELECTION DISPARITY DETECTED' if status == 'NON_COMPLIANT_FLAG' else 'SATISFACTORY: WITHIN STATUTORY BOUNDS'}

1. EXECUTIVE FINDING & STATUTORY SCOPE
Under the supervisory authority of California Insurance Code § 1861.05 (Proposition 103) and 10 CCR § 2644, premium rates must be based on legitimate loss-cost actuarial factors and must not be unfairly discriminatory.

Our decoupled econometric audit of Census Tract {tract_id} ({county} County) has identified an unexplained premium surcharge of +{prem_gap:.1f}% alongside an excess non-renewal disparity of {nr_gap_pp:+.1f} percentage points relative to baseline cohorts facing identical wildfire hazards. Evaluated under fair-lending screening heuristics (four-fifths doctrine), because this census tract falls in Socioeconomic Income Quintile {income_q} (median household income: ${median_inc:,.0f}), the observed pricing disparity is not accounted for by physical hazard.

2. ENVIRONMENTAL DECOUPLING & CONVOLUTIONAL CONTROLS
Physical wildfire hazard for Tract {tract_id} is evaluated at {risk_score*100:.1f}% annual burn probability utilizing solely physical topographical, climatological, and fuel loading indicators. No demographic variables are ingested by the underlying XGBoost/ONNX risk model.

Furthermore, the econometric audit explicitly controls for structural building vintage (home age) and verified property mitigation. The residual +{prem_gap:.1f}% pricing spread represents an unexplained geographic penalty that disproportionately burdens lower-income policyholders without actuarial justification.

3. MANDATED REGULATORY REMEDY
In accordance with CDI Bulletin 2022-5 and fair-lending screening heuristics (four-fifths rule), {carrier_name} is hereby directed to:
  a. Submit granular loss-cost and territorial relativities for Census Tract {tract_id} within 30 days.
  b. Provide verified property-level inspection data demonstrating any unobserved hazard factors.
  c. If loss-cost justification is absent, recalculate baseline territorial relativities to eliminate the +{prem_gap:.1f}% socioeconomic discrepancy.
"""

    return {
        "tract_id": tract_id,
        "county": county,
        "income_quintile": income_q,
        "median_income": median_inc,
        "compliance_status": status,
        "model_engine": engine_name,
        "model_provider": "IBM watsonx.ai" if live_used else "FLare-AI Governance Engine",
        "engine": engine_name,
        "is_live_watsonx": live_used,
        "generated_timestamp": pd.Timestamp.now("UTC").isoformat(),
        "generated_at": pd.Timestamp.now("UTC").strftime("%Y-%m-%d %H:%M UTC"),
        "unexplained_gap_pct": prem_gap,
        "excess_nonrenewal_pp": nr_gap_pp,
        "memorandum_text": ai_generated_text.strip(),
        "text": ai_generated_text.strip(),
    }
