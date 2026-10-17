# AGENT.md: Wildfire Equity Map

## Mission
Build "Wildfire Equity Map" for the IBM Z Datathon (Wildcard: Beyond the Obvious).
The project predicts wildfire risk per California census tract and audits whether
insurance premiums and non-renewals unfairly burden low-income areas AFTER
controlling for actual risk.

Pitch hook: "Two neighborhoods face the same fire risk. One pays three times more,
or gets dropped. We built the tool that shows why."

Judging criteria to keep in mind at every step: clear real-world problem, meaningful
AI + data use, originality, technical ambition, meaningful IBM Z integration,
responsible AI, clear impact, strong data methodology.

## Operating Rules
1. Work in the step order below. After each step: run it, fix errors, write a 3-5 line
   summary of what was done, then continue.
2. Never silently fake results. If a download fails, generate placeholder data and
   label it clearly in code, UI, and docs.
3. Everything must run end to end with one command: `make run` or `python run_all.py`.
4. Keep code simple, typed where useful, and commented where methodology matters.
5. Set random seeds everywhere. Save all parameters to `/data/params.json`.
6. Be honest about limitations in the UI and docs. Do not overclaim.
7. Commit-sized changes: small, tested, reversible.
8. If something is ambiguous, pick the simplest reasonable option, state the
   assumption in the step summary, and keep going.

## Stack
- Python 3.11, pandas, numpy, scikit-learn, XGBoost, statsmodels, SHAP, geopandas
- Streamlit, pydeck or folium (maps), plotly (charts)
- SQLite locally; data-access layer swappable to Db2 for z/OS (`ibm_db`) via env var
  `DB_BACKEND=sqlite|db2`
- pytest for tests

## Folder Layout
```
/data         raw, processed, synthetic data, params.json
/src
  /data       loaders, synthetic generator, db access layer
  /risk_model training, validation, SHAP, scoring
  /audit      regressions, fairness metrics, proxy checks
  /explain    template + optional watsonx.ai explainer
  /ibmz       Db2 DDL, scoring stub, governance logger
/app          Streamlit app
/notebooks    exploration
/docs         ibm_z_architecture.md, methodology.md, pitch notes
/tests
Makefile
run_all.py
README.md
```

## Step 1: Data
- Scope: California census tracts.
- Loaders (or stubs) for: USFS Wildfire Risk to Communities, FEMA National Risk Index,
  Census ACS (median income, race, home value, renter share), CDC SVI.
- On download failure: generate realistic placeholder data, flagged
  `is_placeholder=True` and labeled in the UI.
- Generate SYNTHETIC policies (~200k) assigned to tracts. Fields: tract_id, premium,
  home_age, mitigation_score, non_renewal_flag, denial_flag.
- Premium and non-renewal depend on true risk, plus a hidden, configurable
  income-linked penalty (e.g., `INCOME_PENALTY` in config) so the audit has a known
  effect to recover. Save seed and parameters.
- README note: "Synthetic data calibrated to public aggregates; real policy data is
  private."

## Step 2: Risk Model
- XGBoost predicting tract wildfire risk from ENVIRONMENTAL features only:
  vegetation, slope, drought, fire history, weather.
- NEVER use income, race, or other demographics as model inputs. Enforce with an
  explicit feature allowlist and a test.
- Temporal validation: train on earlier fire seasons, test on later ones. No random
  split.
- Report AUC/RMSE and calibration (plot + metric).
- SHAP global importance plot.
- Output per tract: `risk_score` and `uncertainty` (e.g., bootstrap or quantile range).

## Step 3: Equity Audit
- OLS on log(premium) and logistic regression on non-renewal, with predictors:
  risk_score, home_age, mitigation_score, income_quintile.
- "Unexplained gap" = income-quintile coefficient after controlling for risk.
  Report with confidence intervals.
- Metrics: disparate impact ratio, risk-adjusted non-renewal gap by income group,
  error rates by group.
- Proxy check: test whether ZIP/tract-level features leak income.
- Include a recovery check: the audit must detect the planted synthetic penalty
  within tolerance.

## Step 4: Explainer
- Plain-language one-page summary per tract: risk level, premium vs expected,
  unexplained gap, uncertainty note, plain-English caveats.
- Template-based by default. Optional watsonx.ai call behind `USE_WATSONX=true`,
  always with template fallback. Never hard-code credentials; read from env.

## Step 5: Streamlit App
- Map with toggle layers: risk, premium, non-renewal rate, unexplained gap.
- Scatter: risk vs premium, colored by income quintile.
- Tract detail panel: explainer + uncertainty note.
- Sidebar filters: county, income quintile.
- Persistent banner: "Data is synthetic / placeholder. Demonstration only."
- Must load fast (cache heavy steps) and not crash on missing data.

## Step 6: IBM Z Layer
- DB abstraction supporting SQLite and Db2 for z/OS. Provide Db2 DDL and sample
  queries in `/src/ibmz`.
- Stub scoring endpoint showing in-place scoring at renewal time (ONNX export path
  for Telum).
- Governance logger: JSON per model run with model version, data hash, fairness
  metrics, timestamp (watsonx.governance style). Write to `/data/governance_logs/`.
- `docs/ibm_z_architecture.md` with a Mermaid diagram: data in Db2 for z/OS, scoring
  with Telum, governance logging, Streamlit dashboard.
- Be explicit in docs about what is real, what is stubbed, and what would run on Z in
  production.

## Step 7: Docs and Tests
- README: setup, run commands, methodology, limitations, responsible-AI statement
  (demographics used for auditing only, never for modeling).
- pytest tests:
  1. Synthetic generator: reproducible with seed, correct schema, penalty present.
  2. Audit recovers the planted gap within tolerance.
  3. Risk model features contain no income or demographic columns.
- `make test` must pass before finishing.

## Responsible AI Requirements
- Demographics for auditing only; never as model inputs.
- Show uncertainty and flag thin data.
- Acknowledge that some premium differences are legitimate (older homes, fewer
  mitigations); the audit controls for these.
- State that results are not legal findings or evidence of intent.
- Synthetic data limits real-world claims; lead with method and transparency.

## Definition of Done
- [ ] `make run` launches the app from a clean checkout
- [ ] Audit recovers the planted gap; test passes
- [ ] No-leakage test passes
- [ ] Map, scatter, tract panel, and filters all work
- [ ] Synthetic-data banner visible
- [ ] Architecture doc with Mermaid diagram
- [ ] Governance JSON log produced per run
- [ ] README complete with limitations

## Suggested Checkpoints
1. After Step 3, pause and print the recovered-vs-planted gap before building the app.
2. After Step 5, take screenshots for the pitch deck.
3. Final: run full test suite and a clean-clone smoke test.
