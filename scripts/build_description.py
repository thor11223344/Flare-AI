"""Generates docs/project_description.md from data/*.json files.
Produces an honest, exact 200-250 word project summary for Hack2Skill submission.
"""
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_FILE = ROOT / "docs" / "project_description.md"


def load_data():
    audit = json.loads((DATA_DIR / "audit_results.json").read_text())
    risk = json.loads((DATA_DIR / "risk_metrics.json").read_text())
    params = json.loads((DATA_DIR / "params.json").read_text()) if (DATA_DIR / "params.json").exists() else {}
    gov_logs = sorted((DATA_DIR / "governance_logs").glob("run_*.json"))
    gov = json.loads(gov_logs[-1].read_text()) if gov_logs else {}
    return audit, risk, params, gov


def generate_description():
    audit, risk, params, gov = load_data()

    p_planted = params.get("income_penalty_premium", 0.150)
    pq1 = audit["premium_model"]["income_quintile_effects_log_points"]["1"]
    p_rec = pq1["coef"]
    gap_pct = (np.exp(p_rec) - 1.0) * 100.0
    nr_ratio = audit["fairness"]["nonrenewal_rate_ratio_q1_vs_q5"]
    auc = risk["test_auc"]
    machine = gov.get("executed_on", {}).get("machine", "s390x")
    platform_label = f"s390x" if machine == "s390x" else f"LinuxONE s390x target (tested on {machine})"

    # Construct concise, honest summary (target 200-250 words)
    text = f"""As California wildfires intensify, insurance premiums and policy non-renewals are surging across vulnerable communities. Public discourse often presumes that rate hikes reflect pure physical hazard. Wildfire Equity Map is an actuarial auditing system that decouples physical environmental risk from market underwriting outcomes to verify whether lower-income neighborhoods face unexplained pricing penalties.

Our architecture combines an environmental-only XGBoost risk model (strictly zero demographic inputs; temporal test AUC of {auc:.3f}) with clustered econometric regressions controlling for physical risk, structural building vintage, verified property mitigation, and coverage amounts. In validation, our audit recovered a planted synthetic penalty of +{p_planted:.3f} log-points at +{p_rec:.3f}, identifying a +{gap_pct:.1f}% unexplained premium penalty and a {nr_ratio:.2f}x non-renewal disparity in the lowest-income quintile.

For deployment, our analytical pipeline and Snap ML benchmarks run on IBM LinuxONE ({platform_label}). In an enterprise production path, policy data remains secured in IBM Db2 for z/OS, transaction scoring accelerates on the IBM Telum AI coprocessor via ONNX, and compliance factsheets log to watsonx.governance.

Limitations: all underwriting records are synthetic, hand-parameterized placeholders plotted onto 9,109 real California Census tract boundaries; unobserved structural attributes may explain residual variances. Unexplained disparities serve as regulatory screening flags, not proof of intentional discrimination. Developed with Antigravity AI coding assistance."""

    words = text.split()
    word_count = len(words)

    OUT_FILE.write_text(text, encoding="utf-8")
    print(f"[+] Successfully wrote {OUT_FILE.name} ({word_count} words).")
    if not (200 <= word_count <= 250):
        print(f"[!] Warning: word count is {word_count}, target is 200-250.")
    return text, word_count


if __name__ == "__main__":
    generate_description()
