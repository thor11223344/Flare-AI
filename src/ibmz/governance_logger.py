"""
watsonx.governance Style Lifecycle & Fairness Audit Logger.
Generates regulatory audit logs for enterprise insurance compliance on IBM Z.
Captures model version, data lineage SHA-256 hash, performance metrics,
demographic parity, disparate impact ratios, and four-fifths rule evaluations.
"""

import os
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

GOVERNANCE_DIR = Path("data/governance_logs")

def compute_file_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a dataset for cryptographic data lineage."""
    if not filepath.exists():
        return "file-not-found"
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()

def log_governance_run(
    audit_results_path: str = "data/audit_results.json",
    risk_eval_path: str = "data/risk_model_eval.json",
    params_path: str = "data/params.json",
    tracts_path: str = "data/processed/tracts_with_risk.csv"
) -> Path:
    """
    Generate and save a watsonx.governance-style JSON log.
    """
    GOVERNANCE_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(audit_results_path, "r") as f:
        audit_data = json.load(f)
    with open(risk_eval_path, "r") as f:
        risk_data = json.load(f)
    with open(params_path, "r") as f:
        params_data = json.load(f)

    tracts_hash = compute_file_sha256(Path(tracts_path))
    timestamp_str = datetime.now(timezone.utc).isoformat()
    run_id = f"IBMZ-WATSONX-GOV-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

    # Extract fairness metrics
    dir_q1 = 1.0
    violates_80 = False
    for item in audit_data.get("fairness_metrics", {}).get("disparate_impact_ratios", []):
        if item.get("income_quintile") == 1:
            dir_q1 = item.get("disparate_impact_ratio", 1.0)
            violates_80 = item.get("violates_80pct_rule", False)

    unexplained_gap_q1 = audit_data.get("ols_premium_regression", {}).get("unexplained_gap_q1_vs_q5_pct", 0.0)

    log_entry = {
        "governance_event_id": run_id,
        "timestamp_utc": timestamp_str,
        "platform": {
            "enterprise_host": "IBM z16 (Machine Type 3931)",
            "operating_system": "z/OS v2.5 / Linux on IBM Z",
            "database_system_of_record": "IBM Db2 for z/OS v13",
            "acceleration_engine": "IBM Telum AI On-Chip Coprocessor",
            "governance_plane": "IBM watsonx.governance Enterprise v2.1"
        },
        "model_metadata": {
            "model_name": "Wildfire-Risk-Environmental-XGBoost",
            "model_version": "1.4.0-prod",
            "model_type": "Gradient Boosted Trees (XGBoost / ONNX Runtime)",
            "feature_scope": "STRICT_ENVIRONMENTAL_ONLY (Demographics Strictly Excluded)",
            "input_features": risk_data.get("features", []),
            "target_variable": "fire_occurred (Seasonal Fire Occurrence)"
        },
        "data_lineage": {
            "tracts_with_risk_sha256": tracts_hash,
            "total_tracts_evaluated": params_data.get("n_tracts", 1050),
            "total_policies_audited": params_data.get("total_policies", 200000),
            "data_calibration_status": params_data.get("data_disclaimer", "Synthetic benchmark calibrated to public aggregates")
        },
        "validation_performance": {
            "evaluation_strategy": risk_data.get("validation_strategy", "Temporal Split"),
            "test_roc_auc": risk_data.get("metrics", {}).get("test_roc_auc", 0.0),
            "test_brier_score": risk_data.get("metrics", {}).get("test_brier_score", 0.0),
            "expected_calibration_error": risk_data.get("metrics", {}).get("expected_calibration_error", 0.0)
        },
        "fairness_and_equity_audit": {
            "planted_penalty_benchmark": audit_data.get("recovery_check", {}).get("planted_penalty_coef", 0.0),
            "recovered_penalty_coef": audit_data.get("recovery_check", {}).get("recovered_penalty_coef", 0.0),
            "recovered_penalty_95ci": audit_data.get("recovery_check", {}).get("recovered_penalty_ci_95", []),
            "unexplained_premium_surcharge_q1_pct": unexplained_gap_q1,
            "disparate_impact_ratio_q1": dir_q1,
            "four_fifths_rule_compliant": not violates_80,
            "proxy_leakage_r_squared": audit_data.get("proxy_check", {}).get("r_squared", 0.0)
        },
        "regulatory_compliance_determination": {
            "regulatory_frameworks": [
                "California Department of Insurance (CDI) Wildfire Mitigation Regulations",
                "Consumer Financial Protection Bureau (CFPB) Fair Lending Testing Guidelines",
                "NIST AI Risk Management Framework (AI RMF 1.0)"
            ],
            "compliance_status": "FLAGGED_FOR_HUMAN_OVERSIGHT" if violates_80 else "COMPLIANT",
            "findings_summary": (
                f"AUDIT WARNING: Quintile 1 policies exhibit Disparate Impact Ratio of {dir_q1:.3f} "
                f"(Threshold: 0.800). An unexplained premium surcharge of +{unexplained_gap_q1:.1f}% "
                f"was detected after controlling for physical wildfire risk and home mitigation. "
                "Human regulatory review required before renewal execution."
                if violates_80 else "Model pricing and underwriting adhere to actuarial parity."
            )
        }
    }

    log_filename = GOVERNANCE_DIR / f"watsonx_governance_{run_id}.json"
    latest_filename = GOVERNANCE_DIR / "watsonx_governance_latest.json"
    
    with open(log_filename, "w") as f:
        json.dump(log_entry, f, indent=2)
    with open(latest_filename, "w") as f:
        json.dump(log_entry, f, indent=2)

    return latest_filename

if __name__ == "__main__":
    path = log_governance_run()
    print(f"watsonx.governance log written to: {path}")
