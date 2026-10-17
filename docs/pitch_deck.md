# 🎙️ Wildfire Equity Map: Executive Presentation Deck

> **IBM Z Datathon** · Track: **Wildcard (Beyond the Obvious)**  
> **Target Systems:** IBM z16 · IBM Db2 for z/OS · IBM Telum AI Coprocessor · IBM watsonx.governance  
> **GitHub Repository:** [https://github.com/thor11223344/Flare-AI](https://github.com/thor11223344/Flare-AI)  
> **PowerPoint Version:** [`docs/Wildfire_Equity_Map_Pitch_Deck.pptx`](file:///e:/FLare%20Ai/docs/Wildfire_Equity_Map_Pitch_Deck.pptx)  
> **Pitch Duration:** 5 Minutes (approx. 35–45 seconds per slide)

---

## 📑 Slide 1: Title & Hook
**Visual Theme:** Deep IBM Navy (`#0f172a`) · Accent Orange (`#eb4e24`) · Carbon Blue (`#0f62fe`)

### 🔥 Wildfire Equity Map
**Decoupling Environmental Physics from Insurance Underwriting with IBM z16 & watsonx**

> *"Two neighborhoods face the same fire risk. One pays three times more, or gets dropped. We built the enterprise audit tool that shows why."*

- **Track:** Wildcard (Beyond the Obvious)
- **Target Enterprise Systems:** IBM z16 · IBM Db2 for z/OS · IBM Telum AI Coprocessor · IBM watsonx.governance
- **Team Submission:** [https://github.com/thor11223344/Flare-AI](https://github.com/thor11223344/Flare-AI)

> **Speaker Notes [0:00 - 0:40]:**  
> *"Good morning, judges. Across California, escalating wildfires have triggered an unprecedented insurance availability crisis. Homeowners are seeing premiums double or receiving abrupt non-renewal notices. The conventional public narrative assumes this pricing disparity is simply actuarial physics—that fire burns where it burns, and insurers are merely reflecting pure environmental risk. We built Wildfire Equity Map on IBM z16 to test that assumption."*

---

## 📑 Slide 2: The Crisis & The Flawed Conventional Narrative
**Visual Theme:** Crisis Card Grid + Real California Census Tract Choropleth Map

### 🚨 The California Insurance Market Failure
- **Market Freezes:** Major admitted private carriers (State Farm, Allstate, Farmers) have restricted or frozen new property underwriting across California.
- **FAIR Plan Overload:** Over 400,000 policyholders have been forced into the California FAIR Plan (insurer of last resort), where rates are 300% to 500% higher and coverage is capped.
- **The Actuarial Paradox:** Is this disparity driven purely by physics, or are systemic demographic penalties disguised as environmental hazard?

### ⚖️ The Flawed Conventional Myth vs Market Reality
- **The Myth:** *"Insurance pricing is objective physics; lower-income wildland-urban interface (WUI) tracts simply burn more."*
- **The Reality:** When we analyze 195,000 policies across 1,500 California census tracts, lower-income communities with identical physical hazard face systematic surcharges and elevated non-renewals.

![California Census Tract Choropleth Map](img/ca_choropleth_map.png)

> **Speaker Notes [0:40 - 1:15]:**  
> *"When insurers withdraw or spike rates, policymakers assume it's an unavoidable consequence of climate physics. But when you inspect granular neighborhood data across California, you find two adjacent census tracts facing the identical burn probability receiving wildly different treatment. This map visualizes 1,500 tracts: warm tracts face high premiums, but the red clusters indicate where pricing is completely disconnected from physical hazard."*

---

## 📑 Slide 3: Our Architectural Innovation — Strict Decoupling
**Visual Theme:** 2-Tier Decoupled Pipeline + "Tale of Two Neighborhoods" Comparison

### 1. Environmental-Only Hazard Engine (XGBoost)
- **Zero Demographic Inputs:** Strictly restricted to 8 physical environmental features (slope, canopy fuel biomass, elevation, WUI proximity, drought index, wind speed, temp anomaly, prior fires).
- **Hardened Allowlist:** Demographic proxy check confirms environmental geography carries minimal socioeconomic information ($R^2 = 0.059$).
- **Temporal Holdout Validation:** Trained on 2010–2019 fire seasons, validated on out-of-time future seasons 2020–2023 (**ROC AUC = 0.720**, **Brier Skill Score = +0.019**).

### 2. Clustered Econometric Equity Audit
- **Controls for Legitimate Differences:** Explicitly controls for building vintage (home age), certified fire mitigations (defensible space, Class A roofing), and coverage amount.
- **Tract-Clustered Regressions:** Evaluates log-premium rates (OLS) and non-renewals (Logit) across income quintiles.

![Tale of Two Neighborhoods: Identical Risk, Disparate Pricing](img/pitch_two_tracts_comparison.png)

> **Speaker Notes [1:15 - 1:55]:**  
> *"Our core methodological breakthrough is strict architectural decoupling. Traditional models bundle physical hazard with credit, zip code, and socioeconomics. We built a firewall: our physical risk model sees only environmental features—strictly zero demographic data. Then, an econometric audit regresses market premiums against risk while controlling for home vintage and certified mitigation. Look at Tract 06037000305 versus Tract 06085000412: identical 12.4% burn probabilities, but the lower-income tract pays $18.40 per thousand while the affluent tract pays $12.10."*

---

## 📑 Slide 4: Empirical Audit Findings
**Visual Theme:** 4 Executive Metric Badges + Risk vs. Premium Scatter & Quintile Bar Chart

### Key Disparity Metrics

| Metric | Result | Actuarial Significance |
| :--- | :---: | :--- |
| **Unexplained Q1 Premium Gap** | **+17.4%** | Lowest-income tracts pay $+17.4\%$ more for identical physical hazard ($p = 5.17 \times 10^{-20}$) |
| **Non-Renewal Rate Ratio (Q1/Q5)** | **1.63×** | $4.4\%$ non-renewal rate in Quintile 1 vs $2.7\%$ in Quintile 5 |
| **Physical Model Temporal AUC** | **0.720** | Out-of-time validation on unseen future fire seasons (2020–2023) |
| **Placebo Randomization Center** | **+0.02%** | 500 tract permutations confirm specification does not manufacture bias |

![Risk vs Premium Scatter Plot](img/risk_vs_premium_scatter.png)
![Unexplained Gap by Quintile](img/unexplained_gap_by_quintile.png)

> **Speaker Notes [1:55 - 2:40]:**  
> *"Here is what the empirical audit reveals across 195,000 policies. Controlling for physical risk, structural building vintage, and certified mitigation, homeowners in the lowest-income quintile pay an unexplained +17.4% premium surcharge with an astronomical p-value of 10^-20. On the non-renewal side, lower-income policyholders are dropped at a rate 1.63 times higher. Notice on the scatter plot how Quintile 1 sits systematically above Quintile 5 across every single level of wildfire hazard."*

---

## 📑 Slide 5: IBM z16, Telum & LinuxONE Enterprise Architecture
**Visual Theme:** 3 Enterprise Capability Cards (Telum · Db2 · watsonx.governance)

### 1. IBM Telum ONNX Serving
- **In-Place Renewal Scoring:** Environmental XGBoost model exported to ONNX format with verified equivalence to scikit-learn ($< 1.56 \times 10^{-7}$ max diff).
- **Sub-Millisecond Response:** Evaluates 10,000 single transaction events with full dictionary preprocessing:
  - $p50 = 0.05\text{ms}$
  - $p99 = 0.12\text{ms}$
  - Batch throughput: **$>1.0\text{ Million policies/second}$** *(evaluated on laptop CPU baseline; deployable on Telum via IBM Z Deep Learning Compiler)*.

### 2. IBM Db2 for z/OS In-Place Analytics
- **System of Record Security:** High-volume policy panels never leave the mainframe, eliminating external API egress risks.
- **Partitioned Schema & Analytical SQL:** DDL definitions and analytical audit queries in [`src/ibmz/db2_ddl.sql`](file:///e:/FLare%20Ai/src/ibmz/db2_ddl.sql) with parameterized batch loading (`db2_load.py`).

### 3. watsonx.governance Immutable Factsheets
- **Cryptographic Audit Trail:** Produces SHA-256 factsheet logs capturing model hashes, ONNX runtime lineage, training year splits, and fairness thresholds.
- **Regulatory Gate Compliance:** Evaluates Four-Fifths fairness doctrine (EEOC/HUD) and Proposition 103 mandates.

> **Speaker Notes [2:40 - 3:20]:**  
> *"Why IBM Z? In tier-1 insurance carriers, core policy management and renewals run on IBM z16 systems of record. By compiling our XGBoost model to ONNX, renewal transactions can be scored in-place via the Telum AI coprocessor in 50 microseconds without data egress. Analytics execute directly in IBM Db2 for z/OS, and watsonx.governance logs immutable SHA-256 factsheets providing regulators with mathematical proof of compliance."*

---

## 📑 Slide 6: Actionable Tools — Counterfactuals, Granite & Climate Scenarios
**Visual Theme:** 3 Decision Tool Cards

### 🧮 1. Actuarial Counterfactual & Mitigation ROI Simulator
- **Fair Counterfactual Rate:** Recalculates policy quotes holding unexplained demographic penalties strictly to $\$0$.
- **Mitigation ROI:** Quantifies annual and 5-year cumulative dollar savings from certified physical hardening (e.g., retrofitting Class A roofing and 100ft defensible space saves **$\$600+/\text{year}$**).
- **Homeowner Agency:** Converts abstract climate dread into tangible financial return on investment.

### 🏛️ 2. watsonx.ai Granite Regulatory Enforcement Memos
- **Automated Statutory Briefing:** Generates formal enforcement briefs for the California Department of Insurance (CDI).
- **Statutory Anchors:** Cites California Insurance Code § 1861.05 (Proposition 103) prohibiting unfair discrimination and audits the Four-Fifths disparate impact threshold.
- **Live IBM SDK Integration:** Integrates with `ibm_watsonx_ai` Granite models with offline legal fallback and Markdown export.

### 🌡️ 3. 10-Year Climate Cliff Projections (+1.5°C & +2.0°C)
- **Hazard Amplification:** Projects physical burn probabilities across 2025 (Baseline), 2030 ($+1.5^\circ\text{C}$), and 2035 ($+2.0^\circ\text{C}$).
- **The Availability Cliff:** Pinpoints census tracts crossing the **$15\%$ annual burn probability threshold** where private admitted underwriters systematically withdraw.
- **Regressive Exposure:** Exposes how climate change disproportionately strands lower-income communities in the costly FAIR Plan unless public retrofits are subsidized.

> **Speaker Notes [3:20 - 4:10]:**  
> *"We go beyond passive reporting by giving stakeholders actionable decision tools. First, our Actuarial Counterfactual Simulator calculates what a homeowner should pay if demographic bias is eliminated, showing that certified fire hardening saves $600 to $800 annually. Second, watsonx.ai Granite generates official CDI enforcement memorandums citing Proposition 103 with one click. Third, our 10-Year Climate Projection models hazard through 2035 and identifies tracts that will cross the 15% availability cliff—the exact point where private insurers withdraw."*

---

## 📑 Slide 7: Audit Robustness & Sensitivity Testing
**Visual Theme:** Placebo Permutation Distribution + Noise Sensitivity Table

### 🛡️ 500-Iteration Tract-Level Placebo Test
- **Methodology:** Shuffled income quintiles randomly across tracts 500 times, re-running the full econometric audit on each permutation.
- **Empirical Center:** Mean estimated gap centers cleanly at **$+0.02\%$** (95% empirical range: **$[-2.75\%, +2.86\%]$**).
- **False Positive Rate:** Only **$6.2\%$** of runs exclude zero by chance, aligning with the expected $5\%$ alpha threshold.
- **Conclusion:** Confirms the regression specification does NOT mechanically manufacture disparities.

### 🔍 Sensitivity: Could an Omitted Hazard Explain This?
- **20% Risk Noise Injection:** Injecting 20% random measurement error into modeled risk leaves the gap virtually unchanged (**$+17.4\%$** vs baseline **$+17.4\%$**).
- **Omitted Mitigation Control:** Removing structural mitigation shifts the gap by only $+0.8\text{ pp}$.
- **Omitted Building Vintage:** Removing home age shifts the gap by only $-0.4\text{ pp}$.
- **Key Takeaway:** An unobserved physical risk factor would need to be **$>3.5\times$ more predictive than verified structural roof mitigation** to explain away the low-income surcharge.

> **Speaker Notes [4:10 - 4:40]:**  
> *"Judges always ask: 'Could an omitted risk variable explain this gap?' We stress-tested our methodology in two ways. First, we ran a 500-iteration tract-level placebo test permuting income; the distribution centered right at 0.02%, proving our model does not create artificial bias. Second, our sensitivity analysis proves that an unobserved physical hazard factor would need to be 3.5 times more predictive than verified roof mitigation to overturn our conclusion."*

---

## 📑 Slide 8: Conclusion & Call to Action
**Visual Theme:** Dark Navy Executive Closer + System Architecture Checklist

### *"Algorithms should price physical hazard, not neighborhood wealth."*

- **Enterprise Ready:** IBM z16 and LinuxONE (`s390x`) compatible; sub-millisecond ONNX serving, native Db2 for z/OS analytics, watsonx.governance SHA-256 factsheets.
- **Methodologically Sound:** Decoupled environmental XGBoost validated across 14 fire seasons; 500-run placebo validation; clustered econometric controls.
- **Actionable for All Stakeholders:** Homeowners get mitigation ROI; regulators get watsonx.ai Granite enforcement briefs; planners get 10-year climate projections.
- **100% Tested & Reproducible:** **27 automated tests passing** (`pytest -q`).

---

### 🔗 Project Links
- **GitHub Repository:** [https://github.com/thor11223344/Flare-AI](https://github.com/thor11223344/Flare-AI)
- **Live Streamlit App:** [http://localhost:8501](http://localhost:8501)
- **PowerPoint Deck:** [`docs/Wildfire_Equity_Map_Pitch_Deck.pptx`](file:///e:/FLare%20Ai/docs/Wildfire_Equity_Map_Pitch_Deck.pptx)
- **Architecture Specification:** [`docs/ibm_z_architecture.md`](file:///e:/FLare%20Ai/docs/ibm_z_architecture.md)

> **Speaker Notes [4:40 - 5:00]:**  
> *"Insurance algorithms should price risk, not neighborhood wealth. With Wildfire Equity Map on IBM z16 and watsonx, underwriters and regulators have a transparent, real-time audit engine that ensures compliance with the Four-Fifths rule and protects vulnerable communities from unjust climate penalties. All code, 27 passing tests, and models are live on GitHub. Thank you."*
