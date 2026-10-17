"""Unit tests for Phase 4: Robustness (Bootstrap CI, Placebo permutation test)
and Sensitivity Analysis in econometric audit.
"""
import pytest
import numpy as np
import pandas as pd
from src.audit import audit
from src import config


def test_audit_robustness_bootstrap_and_placebo(pipeline):
    """Verify that bootstrap CI bounds and tract-level placebo test are computed."""
    df = audit.build_frame()
    rob = audit.run_robustness(df, n_boot=8, n_placebo=10, seed=42)

    assert "bootstrap_q1" in rob
    boot = rob["bootstrap_q1"]
    assert len(boot["ci_95"]) == 2
    assert boot["ci_95"][0] < boot["ci_95"][1]
    # Point estimate should be positive for lowest income quintile surcharge
    assert boot["ci_95"][0] > 0.05

    assert "placebo_test" in rob
    placebo = rob["placebo_test"]
    assert placebo["shuffled_level"] == "tract"
    assert "mean_gap_pct" in placebo
    assert "percentile_range_pct" in placebo
    assert "ci_excludes_zero_share_pct" in placebo
    # Tract-level shuffled income label should yield placebo effect close to zero (< 2.0% gap)
    assert abs(placebo["mean_gap_pct"]) < 2.0
    assert placebo["passed"] is True


def test_audit_sensitivity_omitted_variables(pipeline):
    """Verify that sensitivity analysis detects impact of omitted mitigation and risk noise."""
    df = audit.build_frame()
    sens = audit.sensitivity_analysis(df, seed=42)

    assert "baseline" in sens
    assert "omitted_mitigation" in sens
    assert "risk_noise_20pct" in sens
    assert "omitted_home_age" in sens

    # Omitting mitigation should increase the unexplained penalty
    assert sens["omitted_mitigation"]["gap_pct"] > sens["baseline"]["gap_pct"]

    # 20% risk measurement noise should not distort the gap dramatically (within 3 percentage points)
    assert abs(sens["risk_noise_20pct"]["delta_pct"]) < 3.0
