"""
Synthetic Data Generator for Wildfire Equity Map.
Generates realistic California census tract risk/demographic indicators
and ~200,000 synthetic insurance policies with an intentional, planted
income penalty for equity audit recovery verification.
"""

import os
import json
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from pathlib import Path

DEFAULT_SEED = 42

# California counties and their approximate geographic/wildfire characteristics
CA_COUNTIES = [
    {"county": "Alameda", "fips": "001", "lat": 37.65, "lon": -121.90, "base_risk": 0.22, "mean_income": 112000, "wui_share": 0.25},
    {"county": "Alpine", "fips": "003", "lat": 38.60, "lon": -119.82, "base_risk": 0.88, "mean_income": 68000, "wui_share": 0.90},
    {"county": "Amador", "fips": "005", "lat": 38.45, "lon": -120.65, "base_risk": 0.78, "mean_income": 72000, "wui_share": 0.85},
    {"county": "Butte", "fips": "007", "lat": 39.67, "lon": -121.60, "base_risk": 0.85, "mean_income": 62000, "wui_share": 0.75},
    {"county": "Calaveras", "fips": "009", "lat": 38.20, "lon": -120.55, "base_risk": 0.80, "mean_income": 70000, "wui_share": 0.80},
    {"county": "Contra Costa", "fips": "013", "lat": 37.92, "lon": -121.93, "base_risk": 0.35, "mean_income": 110000, "wui_share": 0.30},
    {"county": "El Dorado", "fips": "017", "lat": 38.78, "lon": -120.53, "base_risk": 0.86, "mean_income": 88000, "wui_share": 0.82},
    {"county": "Fresno", "fips": "019", "lat": 36.75, "lon": -119.65, "base_risk": 0.45, "mean_income": 61000, "wui_share": 0.35},
    {"county": "Humboldt", "fips": "023", "lat": 40.70, "lon": -123.87, "base_risk": 0.65, "mean_income": 54000, "wui_share": 0.70},
    {"county": "Kern", "fips": "029", "lat": 35.34, "lon": -118.73, "base_risk": 0.55, "mean_income": 58000, "wui_share": 0.40},
    {"county": "Lake", "fips": "033", "lat": 39.10, "lon": -122.75, "base_risk": 0.89, "mean_income": 53000, "wui_share": 0.88},
    {"county": "Los Angeles", "fips": "037", "lat": 34.05, "lon": -118.25, "base_risk": 0.38, "mean_income": 77000, "wui_share": 0.28},
    {"county": "Marin", "fips": "041", "lat": 38.07, "lon": -122.72, "base_risk": 0.50, "mean_income": 131000, "wui_share": 0.55},
    {"county": "Mendocino", "fips": "045", "lat": 39.44, "lon": -123.43, "base_risk": 0.82, "mean_income": 58000, "wui_share": 0.80},
    {"county": "Monterey", "fips": "053", "lat": 36.22, "lon": -121.32, "base_risk": 0.60, "mean_income": 76000, "wui_share": 0.48},
    {"county": "Napa", "fips": "055", "lat": 38.50, "lon": -122.33, "base_risk": 0.79, "mean_income": 97000, "wui_share": 0.72},
    {"county": "Nevada", "fips": "057", "lat": 39.30, "lon": -120.77, "base_risk": 0.87, "mean_income": 74000, "wui_share": 0.85},
    {"county": "Orange", "fips": "059", "lat": 33.72, "lon": -117.83, "base_risk": 0.32, "mean_income": 100000, "wui_share": 0.22},
    {"county": "Placer", "fips": "061", "lat": 39.06, "lon": -120.72, "base_risk": 0.74, "mean_income": 99000, "wui_share": 0.68},
    {"county": "Riverside", "fips": "065", "lat": 33.74, "lon": -116.50, "base_risk": 0.58, "mean_income": 73000, "wui_share": 0.45},
    {"county": "Sacramento", "fips": "067", "lat": 38.47, "lon": -121.45, "base_risk": 0.20, "mean_income": 76000, "wui_share": 0.15},
    {"county": "San Bernardino", "fips": "071", "lat": 34.84, "lon": -116.18, "base_risk": 0.62, "mean_income": 70000, "wui_share": 0.50},
    {"county": "San Diego", "fips": "073", "lat": 33.02, "lon": -116.77, "base_risk": 0.64, "mean_income": 88000, "wui_share": 0.52},
    {"county": "San Francisco", "fips": "075", "lat": 37.77, "lon": -122.42, "base_risk": 0.05, "mean_income": 126000, "wui_share": 0.02},
    {"county": "San Mateo", "fips": "081", "lat": 37.43, "lon": -122.28, "base_risk": 0.38, "mean_income": 136000, "wui_share": 0.35},
    {"county": "Santa Barbara", "fips": "083", "lat": 34.65, "lon": -119.85, "base_risk": 0.68, "mean_income": 84000, "wui_share": 0.58},
    {"county": "Santa Clara", "fips": "085", "lat": 37.23, "lon": -121.69, "base_risk": 0.30, "mean_income": 140000, "wui_share": 0.25},
    {"county": "Santa Cruz", "fips": "087", "lat": 37.05, "lon": -121.99, "base_risk": 0.72, "mean_income": 96000, "wui_share": 0.65},
    {"county": "Shasta", "fips": "089", "lat": 40.76, "lon": -122.04, "base_risk": 0.84, "mean_income": 58000, "wui_share": 0.78},
    {"county": "Sonoma", "fips": "097", "lat": 38.52, "lon": -122.88, "base_risk": 0.81, "mean_income": 91000, "wui_share": 0.70},
    {"county": "Trinity", "fips": "105", "lat": 40.65, "lon": -123.11, "base_risk": 0.87, "mean_income": 45000, "wui_share": 0.92},
    {"county": "Tulare", "fips": "107", "lat": 36.22, "lon": -118.80, "base_risk": 0.60, "mean_income": 57000, "wui_share": 0.45},
    {"county": "Tuolumne", "fips": "109", "lat": 38.03, "lon": -119.95, "base_risk": 0.85, "mean_income": 65000, "wui_share": 0.88},
    {"county": "Ventura", "fips": "111", "lat": 34.46, "lon": -119.08, "base_risk": 0.70, "mean_income": 94000, "wui_share": 0.60},
    {"county": "Yolo", "fips": "113", "lat": 38.69, "lon": -121.90, "base_risk": 0.30, "mean_income": 78000, "wui_share": 0.20},
]

def generate_california_tracts(
    n_tracts_per_county: int = 30,
    seed: int = DEFAULT_SEED
) -> pd.DataFrame:
    """
    Generate realistic California census tracts with environmental, demographic,
    and temporal wildfire risk indicators.
    """
    rng = np.random.default_rng(seed)
    records = []

    for c in CA_COUNTIES:
        for i in range(1, n_tracts_per_county + 1):
            tract_fips = f"06{c['fips']}{i:06d}"
            # Spatial jitter around county centroid
            lat = c['lat'] + rng.normal(0, 0.08)
            lon = c['lon'] + rng.normal(0, 0.08)
            
            # WUI classification
            is_wui = int(rng.random() < c['wui_share'])
            
            # Environmental variables (ONLY these are allowed in the risk model)
            slope = np.clip(rng.gamma(shape=2.5, scale=4.0) + (12.0 if is_wui else 2.0), 0.5, 45.0)
            canopy = np.clip(rng.beta(2, 2) * 80.0 + (15.0 if is_wui else 0.0), 2.0, 95.0)
            fuel_load = np.clip(rng.gamma(shape=2.0, scale=2.5) + (3.0 if is_wui else 0.5), 0.2, 18.0)
            wind_speed = np.clip(rng.normal(12.0, 3.5) + (3.0 if slope > 20 else 0.0), 3.0, 35.0)
            days_hot = np.clip(int(rng.normal(35, 14)), 2, 85)
            spei_drought = np.clip(rng.normal(-0.8, 0.7), -3.0, 1.5) # negative = dry
            burn_hist_20yr = int(rng.poisson(lam=max(0.1, c['base_risk'] * 2.2)))
            vcf_dryness = np.clip(rng.beta(3, 2) * 0.7 + (-spei_drought * 0.08), 0.05, 0.98)
            temp_mean_c = np.clip(rng.normal(16.5, 3.2), 8.0, 26.0)

            # Ground truth environmental risk (physical hazard, 0.0 to 1.0)
            # Log-odds of high fire hazard from physical features only
            hazard_logit = (
                -3.2
                + 0.045 * slope
                + 0.025 * canopy
                + 0.12 * fuel_load
                + 0.06 * wind_speed
                + 0.015 * days_hot
                - 0.45 * spei_drought
                + 0.35 * burn_hist_20yr
                + 0.8 * vcf_dryness
            )
            true_risk_score = 1.0 / (1.0 + np.exp(-hazard_logit))
            
            # Demographic variables (strictly for auditing, NOT modeling)
            inc_base = c['mean_income'] * np.exp(rng.normal(0, 0.35))
            median_income = np.clip(inc_base, 22000, 260000)
            
            # Racial composition
            pct_white = np.clip(rng.normal(0.48, 0.18), 0.05, 0.90)
            pct_hispanic = np.clip(rng.normal(0.32, 0.15), 0.05, 0.85)
            pct_black = np.clip(rng.normal(0.06, 0.05), 0.01, 0.45)
            pct_asian = np.clip(rng.normal(0.12, 0.09), 0.01, 0.50)
            tot_race = pct_white + pct_hispanic + pct_black + pct_asian
            pct_white /= tot_race
            pct_hispanic /= tot_race
            pct_black /= tot_race
            pct_asian /= tot_race
            
            renter_share = np.clip(0.65 - (median_income / 350000) + rng.normal(0, 0.08), 0.05, 0.90)
            home_val = np.clip(median_income * rng.uniform(6.0, 11.0), 160000, 2400000)
            
            # CDC Social Vulnerability Index (SVI: 0 = least vulnerable, 1 = most vulnerable)
            svi_score = np.clip(1.0 - (median_income / 220000) * 0.8 + rng.normal(0, 0.1), 0.01, 0.99)
            
            records.append({
                "tract_id": tract_fips,
                "county": c["county"],
                "county_fips": c["fips"],
                "latitude": round(lat, 5),
                "longitude": round(lon, 5),
                "wui_flag": is_wui,
                # Environmental features (Model inputs)
                "mean_slope_deg": round(slope, 2),
                "canopy_cover_pct": round(canopy, 2),
                "surface_fuel_loading": round(fuel_load, 2),
                "mean_wind_speed_mph": round(wind_speed, 2),
                "days_above_35c": days_hot,
                "drought_index_spei": round(spei_drought, 2),
                "historic_burn_count_20yr": burn_hist_20yr,
                "vegetation_dryness_vcf": round(vcf_dryness, 3),
                "mean_annual_temp_c": round(temp_mean_c, 2),
                "true_risk_score": round(true_risk_score, 4),
                # Demographic features (Audit only)
                "median_household_income": round(median_income, 0),
                "pct_white": round(pct_white, 3),
                "pct_hispanic": round(pct_hispanic, 3),
                "pct_black": round(pct_black, 3),
                "pct_asian": round(pct_asian, 3),
                "renter_share": round(renter_share, 3),
                "median_home_value": round(home_val, 0),
                "cdc_svi_score": round(svi_score, 3),
                "is_placeholder": True,
                "data_source": "Calibrated USFS/FEMA/Census Placeholder"
            })

    df = pd.DataFrame(records)
    
    # Compute statewide income quintiles (1 = Lowest, 5 = Highest)
    df["income_quintile"] = pd.qcut(
        df["median_household_income"],
        q=5,
        labels=[1, 2, 3, 4, 5]
    ).astype(int)
    
    return df

def generate_temporal_panel(
    tracts_df: pd.DataFrame,
    start_season: int = 2016,
    end_season: int = 2024,
    split_season: int = 2021,
    seed: int = DEFAULT_SEED
) -> pd.DataFrame:
    """
    Generate seasonal fire occurrence records for temporal validation.
    Train seasons: 2016-2020. Test seasons: 2021-2024.
    """
    rng = np.random.default_rng(seed + 10)
    rows = []
    
    for season in range(start_season, end_season + 1):
        # Season-specific climate severity multiplier (e.g. 2017, 2020, 2021 were severe CA fire seasons)
        severity_offset = 0.45 if season in [2017, 2020, 2021] else -0.20
        
        for _, tract in tracts_df.iterrows():
            # Physical hazard logit from environmental features
            phys_logit = (
                -2.8
                + 0.045 * tract["mean_slope_deg"]
                + 0.025 * tract["canopy_cover_pct"]
                + 0.12 * tract["surface_fuel_loading"]
                + 0.05 * tract["mean_wind_speed_mph"]
                + 0.015 * tract["days_above_35c"]
                - 0.40 * tract["drought_index_spei"]
                + 0.35 * tract["historic_burn_count_20yr"]
                + 0.75 * tract["vegetation_dryness_vcf"]
                + severity_offset
                + rng.normal(0, 0.45)
            )
            p_fire = 1.0 / (1.0 + np.exp(-phys_logit))
            fire_occurred = int(rng.random() < p_fire)
            
            # Acres burned fraction given fire
            burned_fraction = rng.beta(2.0, 7.0) * tract["true_risk_score"] if fire_occurred else 0.0
            
            rows.append({
                "tract_id": tract["tract_id"],
                "season": season,
                "is_train_season": int(season < split_season),
                "mean_slope_deg": tract["mean_slope_deg"],
                "canopy_cover_pct": tract["canopy_cover_pct"],
                "surface_fuel_loading": tract["surface_fuel_loading"],
                "mean_wind_speed_mph": tract["mean_wind_speed_mph"],
                "days_above_35c": tract["days_above_35c"],
                "drought_index_spei": tract["drought_index_spei"],
                "historic_burn_count_20yr": tract["historic_burn_count_20yr"],
                "vegetation_dryness_vcf": tract["vegetation_dryness_vcf"],
                "mean_annual_temp_c": tract["mean_annual_temp_c"],
                "fire_occurred": fire_occurred,
                "burned_area_fraction": round(burned_fraction, 4)
            })
            
    return pd.DataFrame(rows)

def generate_synthetic_policies(
    tracts_df: pd.DataFrame,
    total_policies: int = 200000,
    planted_income_penalty_coef: float = 0.05, # +5% log premium per quintile drop (Q1 vs Q5 = +20%)
    planted_non_renewal_penalty: float = 0.20, # higher non-renewal log-odds for lower income
    seed: int = DEFAULT_SEED
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Generate ~200,000 synthetic homeowner policies across tracts.
    Embeds an intentional, hidden income-linked penalty so the equity audit
    has a verified, calibrated ground-truth effect to detect and recover.
    """
    rng = np.random.default_rng(seed + 100)
    n_tracts = len(tracts_df)
    
    # Allocate policies across tracts proportional to housing density / home value
    weights = tracts_df["median_home_value"].values / tracts_df["median_home_value"].sum()
    policies_per_tract = rng.multinomial(total_policies, weights)
    
    records = []
    policy_id_counter = 1
    
    for idx, (_, tract) in enumerate(tracts_df.iterrows()):
        n_p = policies_per_tract[idx]
        if n_p == 0:
            continue
            
        t_id = tract["tract_id"]
        county = tract["county"]
        risk = tract["true_risk_score"]
        q = tract["income_quintile"] # 1 to 5
        med_inc = tract["median_household_income"]
        
        # Policy-level characteristics
        home_ages = np.clip(rng.normal(38.0, 18.0, size=n_p), 1, 95)
        # Mitigation score: 0 to 1 (defensible space, fire-rated roof, mesh vents)
        # Low-income areas on average have slightly lower mitigation resources, but wide variation
        mit_scores = np.clip(rng.beta(2.5, 2.0, size=n_p) * 0.8 + (q * 0.03), 0.05, 0.98)
        
        # Actuarial Base Premium:
        # Base ~$1,200/yr, scaling exponentially with true risk, home age, and mitigation discount
        # Planted Income Penalty: lower income quintiles get charged an extra surcharge
        # Penalty formula: (5 - q) * planted_income_penalty_coef in log space
        # For Q5 (wealthiest): penalty = 0. For Q1 (lowest): penalty = 4 * 0.05 = +0.20 in log premium (~+22% higher)
        log_premium_true_risk_part = 1.65 * risk
        log_premium_age_part = 0.004 * home_ages
        log_premium_mit_discount = -0.45 * mit_scores
        log_premium_planted_penalty = (5 - q) * planted_income_penalty_coef
        
        noise_premium = rng.normal(0, 0.12, size=n_p)
        
        log_premium = (
            np.log(1250.0)
            + log_premium_true_risk_part
            + log_premium_age_part
            + log_premium_mit_discount
            + log_premium_planted_penalty
            + noise_premium
        )
        premiums = np.round(np.exp(log_premium), 2)
        
        # Non-renewal logit:
        # P(non-renewal) depends strongly on risk and age, reduced by mitigation,
        # PLUS an intentional hidden penalty against lower-income areas
        logit_nr = (
            -3.4
            + 3.2 * risk
            + 0.012 * home_ages
            - 1.5 * mit_scores
            + (5 - q) * planted_non_renewal_penalty
            + rng.normal(0, 0.15, size=n_p)
        )
        p_nr = 1.0 / (1.0 + np.exp(-logit_nr))
        non_renewals = (rng.random(size=n_p) < p_nr).astype(int)
        
        # Denial flag: new coverage application denial
        logit_denial = logit_nr - 0.4
        p_denial = 1.0 / (1.0 + np.exp(-logit_denial))
        denials = (rng.random(size=n_p) < p_denial).astype(int)
        
        p_ids = [f"POL-{policy_id_counter + k:07d}" for k in range(n_p)]
        policy_id_counter += n_p
        
        sub_df = pd.DataFrame({
            "policy_id": p_ids,
            "tract_id": t_id,
            "county": county,
            "home_age": np.round(home_ages, 1),
            "mitigation_score": np.round(mit_scores, 3),
            "true_risk_score": round(risk, 4),
            "income_quintile": q,
            "tract_median_income": round(med_inc, 0),
            "premium": premiums,
            "log_premium": np.round(log_premium, 4),
            "non_renewal_flag": non_renewals,
            "denial_flag": denials
        })
        records.append(sub_df)
        
    policies_df = pd.concat(records, ignore_index=True)
    
    metadata = {
        "generator_seed": seed,
        "total_policies": int(len(policies_df)),
        "planted_income_penalty_coef": planted_income_penalty_coef,
        "planted_non_renewal_penalty": planted_non_renewal_penalty,
        "expected_log_premium_q1_vs_q5_gap": round(4 * planted_income_penalty_coef, 4),
        "note": "Synthetic data calibrated to public aggregates; real policy data is private."
    }
    
    return policies_df, metadata
