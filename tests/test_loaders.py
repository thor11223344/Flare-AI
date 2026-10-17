"""Unit tests for Phase 2: Public data loaders (Census ACS, FEMA NRI, CDC SVI)
and tracts.csv builder with offline fallback.
"""
from pathlib import Path
import pytest
import pandas as pd
from src.data import loaders
from src import config


def test_census_acs_loader_schema_and_fallback(tmp_path, monkeypatch):
    """Verify Census ACS loader returns valid schema with offline fallback."""
    # Run in temp directory to verify fallback without network
    monkeypatch.setattr(loaders, "RAW_DIR", tmp_path)
    monkeypatch.setattr(loaders, "CENSUS_CACHE", tmp_path / "census_acs_ca_tracts.csv")

    df = loaders.load_census_acs(api_key="INVALID_TEST_KEY", max_retries=1, force=True)
    assert df is not None
    assert len(df) > 0
    expected_cols = {"tract_id", "median_income", "median_home_value", "renter_share", "pct_minority", "is_placeholder"}
    assert expected_cols <= set(df.columns)
    assert (df["median_income"] > 0).all()
    assert (df["is_placeholder"] == 1).all()


def test_fema_nri_loader_schema_and_fallback(tmp_path, monkeypatch):
    """Verify FEMA NRI loader produces valid hazard & exposure fields."""
    monkeypatch.setattr(loaders, "RAW_DIR", tmp_path)
    monkeypatch.setattr(loaders, "FEMA_CACHE", tmp_path / "fema_nri_ca_tracts.csv")

    df = loaders.load_fema_nri(max_retries=1, force=True)
    assert df is not None
    assert len(df) > 0
    expected_cols = {"tract_id", "vegetation", "slope", "elevation", "wui_proximity", "drought_base", "wind_base", "is_placeholder"}
    assert expected_cols <= set(df.columns)
    assert ((df["vegetation"] >= 0) & (df["vegetation"] <= 1)).all()
    assert ((df["wui_proximity"] >= 0) & (df["wui_proximity"] <= 1)).all()


def test_cdc_svi_loader_schema_and_fallback(tmp_path, monkeypatch):
    """Verify CDC SVI loader produces valid vulnerability index."""
    monkeypatch.setattr(loaders, "RAW_DIR", tmp_path)
    monkeypatch.setattr(loaders, "CDC_CACHE", tmp_path / "cdc_svi_ca_tracts.csv")

    df = loaders.load_cdc_svi(max_retries=1, force=True)
    assert df is not None
    assert len(df) > 0
    assert {"tract_id", "svi", "is_placeholder"} <= set(df.columns)
    assert ((df["svi"] >= 0) & (df["svi"] <= 1)).all()


def test_build_real_or_calibrated_tracts_csv(tmp_path, monkeypatch):
    """Verify building the unified data/raw/tracts.csv table."""
    monkeypatch.setattr(loaders, "RAW_DIR", tmp_path)
    monkeypatch.setattr(loaders, "CENSUS_CACHE", tmp_path / "census_acs_ca_tracts.csv")
    monkeypatch.setattr(loaders, "FEMA_CACHE", tmp_path / "fema_nri_ca_tracts.csv")
    monkeypatch.setattr(loaders, "CDC_CACHE", tmp_path / "cdc_svi_ca_tracts.csv")
    monkeypatch.setattr(loaders, "TRACTS_CSV", tmp_path / "tracts.csv")

    out_path = loaders.build_real_or_calibrated_tracts_csv(n_sample=100, seed=42)
    assert out_path.exists()
    t = pd.read_csv(out_path)
    assert len(t) == 100

    required = [
        "tract_id", "county", "lat", "lon", "vegetation", "slope", "elevation",
        "wui_proximity", "drought_base", "wind_base", "median_income",
        "median_home_value", "pct_minority", "renter_share", "svi", "is_placeholder"
    ]
    for col in required:
        assert col in t.columns, f"Missing {col} in built tracts.csv"
