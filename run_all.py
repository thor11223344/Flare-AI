"""One command: generate data -> train risk model -> audit -> governance log -> launch app.

python run_all.py              # full pipeline, then launches Streamlit
python run_all.py --no-app     # pipeline only
python run_all.py --force      # regenerate everything
python run_all.py --real-tracts # build real public tracts (ACS/NRI/SVI) with fallback
"""
import sys
import subprocess
from src import config
from src.data import generate, db, loaders
from src.risk_model import train
from src.audit import audit
from src.ibmz import governance


def pipeline(force=False, real_tracts=False):
    if real_tracts:
        print("[0/4] Building tracts dataset from public data loaders (ACS/NRI/SVI)...")
        loaders.build_real_or_calibrated_tracts_csv(n_sample=config.N_TRACTS, seed=config.SEED)
        force = True

    if force or not db.table_exists("policies"):
        print("[1/4] Generating data & synthetic policies..."); print("     ", generate.run()["n_policies"], "policies")
    else:
        print("[1/4] Data exists (use --force to regenerate)")
    print("[2/4] Training risk model (temporal split)...")
    m = train.train_and_score()
    print(f"      test AUC={m['test_auc']:.3f}  Brier skill={m['brier_skill']:.3f}  calib MAE={m['calibration_mae']:.4f}")
    print("[3/4] Running equity audit...")
    a = audit.run()
    r = a["recovery"]
    print(f"      premium gap Q1: est {r['estimated_premium_gap_q1']:.3f} vs planted {r['planted_premium_penalty_q1']:.3f} "
          f"(recovered={r['premium_recovered']})")
    print("      " + a["interpretation"])
    print("[4/4] Governance log:", governance.log_run(m, a))


if __name__ == "__main__":
    force_run = "--force" in sys.argv
    real_tracts_run = "--real-tracts" in sys.argv
    pipeline(force=force_run, real_tracts=real_tracts_run)
    if "--no-app" not in sys.argv:
        subprocess.run([sys.executable, "-m", "streamlit", "run", str(config.ROOT / "app" / "streamlit_app.py")])

