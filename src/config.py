"""Central configuration. Every knob that affects data or methodology lives here."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("WF_DATA_DIR", ROOT / "data"))
DATA_DIR.mkdir(exist_ok=True)

SEED = int(os.getenv("SEED", 42))
N_TRACTS = int(os.getenv("N_TRACTS", 1500))
POLICIES_PER_TRACT = int(os.getenv("POLICIES_PER_TRACT", 130))  # ~195k policies
YEARS = list(range(2010, 2024))
TRAIN_YEARS = list(range(2010, 2020))   # earlier fire seasons
TEST_YEARS = list(range(2020, 2024))    # later fire seasons (temporal holdout)

# Planted bias the audit must recover (log-points on premium, log-odds on non-renewal
# for the LOWEST income quintile vs the HIGHEST; scales linearly across quintiles).
INCOME_PENALTY_PREMIUM = float(os.getenv("INCOME_PENALTY_PREMIUM", 0.15))
INCOME_PENALTY_NONRENEWAL = float(os.getenv("INCOME_PENALTY_NONRENEWAL", 0.50))

# Risk model may ONLY see these (allowlist). Demographics are for auditing, never modeling.
ENV_FEATURES = ["vegetation", "slope", "elevation", "wui_proximity",
                "drought_index", "wind_speed", "temp_anomaly", "fires_prior5"]
FORBIDDEN_FEATURES = ["median_income", "income_quintile", "pct_minority", "median_home_value",
                      "renter_share", "svi", "premium", "non_renewal", "denial"]

DB_BACKEND = os.getenv("DB_BACKEND", "sqlite")
SQLITE_PATH = Path(os.getenv("SQLITE_PATH", DATA_DIR / "wildfire.db"))
DB2_DSN = os.getenv("DB2_DSN", "")
USE_WATSONX = os.getenv("USE_WATSONX", "false").lower() == "true"

SYNTHETIC_NOTE = ("Synthetic data calibrated to public aggregates; real policy data is private. "
                  "Tract geometry is replaced by centroids; environmental/demographic values are "
                  "placeholders unless real loaders are enabled.")
