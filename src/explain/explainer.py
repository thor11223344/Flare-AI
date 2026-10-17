"""Plain-language tract explainers. Template by default; optional watsonx.ai behind USE_WATSONX=true."""
import os
import pandas as pd
from src import config


def _risk_label(pct: float) -> str:
    return ("very high" if pct >= 0.9 else "high" if pct >= 0.7 else "moderate" if pct >= 0.4 else "low")


def _gap_label(pct: float, se: float) -> str:
    if abs(pct) < 2 * se or abs(pct) < 3:
        return "no clear unexplained difference"
    return f"about {abs(pct):.0f}% {'more' if pct > 0 else 'less'} than expected"


def template_summary(r: pd.Series) -> str:
    risk = _risk_label(r.risk_percentile)
    gap = _gap_label(r.premium_gap_pct, r.premium_gap_pct_se)
    nr_pp = r.nr_gap_pp * 100
    nr_txt = ("non-renewals are in line with what risk predicts" if abs(nr_pp) < 1.0 else
              f"non-renewals run {abs(nr_pp):.1f} percentage points {'above' if nr_pp > 0 else 'below'} what risk predicts")
    return (
        f"**Tract {r.tract_id} ({r.county} County)**\n\n"
        f"- **Wildfire risk:** {risk} (higher than {r.risk_percentile * 100:.0f}% of tracts; modeled annual burn "
        f"probability {r.risk_score * 100:.1f}%, plausible range {r.risk_lo * 100:.1f}% to {r.risk_hi * 100:.1f}%).\n"
        f"- **Neighborhood income:** quintile {int(r.income_quintile)} of 5 (1 = lowest), median ${r.median_income:,.0f}.\n"
        f"- **Typical premium:** ${r.avg_premium:,.0f} a year. After accounting for risk, home age, mitigation and "
        f"coverage, homeowners here pay {gap} compared with the highest-income areas.\n"
        f"- **Coverage:** {r.nonrenewal_rate * 100:.1f}% of policies were not renewed; {nr_txt}.\n\n"
        f"*How to read this:* a gap is a flag for review, not proof of unfair intent. Some price differences are "
        f"legitimate (older roofs, fewer mitigation measures). Data is synthetic/placeholder and estimates carry "
        f"uncertainty (about {r.n_policies} policies in this tract)."
    )


def watsonx_summary(r: pd.Series) -> str:
    from ibm_watsonx_ai.foundation_models import ModelInference  # pip install ibm-watsonx-ai
    model = ModelInference(model_id=os.getenv("WATSONX_MODEL", "ibm/granite-3-8b-instruct"),
                           credentials=dict(url=os.getenv("WATSONX_URL"), api_key=os.getenv("WATSONX_APIKEY")),
                           project_id=os.getenv("WATSONX_PROJECT_ID"),
                           params=dict(max_new_tokens=350, temperature=0.2))
    prompt = ("Rewrite this wildfire insurance equity summary for a homeowner at an 8th-grade reading level. "
              "Keep every number exact, add no new facts, and keep the caveat that a gap is not proof of intent.\n\n"
              + template_summary(r))
    return model.generate_text(prompt)


def explain(r: pd.Series) -> str:
    if config.USE_WATSONX:
        try:
            return watsonx_summary(r)
        except Exception:
            pass  # always fall back to the deterministic template
    return template_summary(r)
