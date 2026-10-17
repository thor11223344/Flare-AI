# Wildfire Equity Map — 3-Minute Demo Video Script
**Track:** Wildcard (Beyond the Obvious) | **Datathon:** IBM Z Datathon 2026  
**Target Duration:** Exactly 3:00 (180 seconds)  
**Speaker/Presenter:** Team Thor  

---

## Technical & Honest Disclosures (Mandatory)
- **Data Status:** Policy underwriting and demographic data are synthetic, hand-parameterized research placeholders mapped onto 9,109 real California Census tract boundaries (`cb_2022_06_tract_500k`), not real private insurer or confidential Census data.
- **Hardware Status:** The analytical pipeline and Snap ML benchmarks were executed on an IBM LinuxONE virtual machine (s390x architecture; local tests on AMD64). In-place Db2 for z/OS analytics, the IBM Telum AI coprocessor via ONNX/zDLC, and watsonx.governance represent our enterprise production roadmap (untested in this hackathon environment).
- **AI Tooling:** Developed with assistance from Google Antigravity AI coding tools.

---

## Segment Breakdown & Timestamps

### 1. Hook & Problem Framing (0:00 – 0:25 | 25s)
* **Screen Action:**  
  Start on browser showing Streamlit application header: **"Wildfire Equity Map"** with the tagline visible: *"Two neighborhoods face the same fire risk. One pays more. We built the tool that shows why."* Zoom out slightly to show California statewide overview with tract boundaries.
* **Narration:**  
  "Across California, climate risk is driving unprecedented homeowners insurance non-renewals and premium shocks. But when rates spike, how do regulators or homeowners know whether the price hike reflects physical wildfire hazard, or unexplained socioeconomic disparity?  
  Today, we present **Wildfire Equity Map**—an open actuarial auditing system that decouples physical hazard from market pricing to detect unexplained rate gaps."

---

### 2. Physical Hazard vs. Pricing Map Layers (0:25 – 0:55 | 30s)
* **Screen Action:**  
  Toggle between map layers in the Streamlit sidebar:
  1. Select **"Physical Hazard Score"** — choropleth shades from green to dark red across Sierra foothills and Southern California wildland-urban interfaces.
  2. Switch dropdown to **"Actual / Quoted Premium"**.
  3. Switch dropdown to **"Unexplained Premium Gap (Equity Audit)"**. Show high-penalty clusters highlighted in amber/purple.
* **Narration:**  
  "Here in the interactive dashboard, our first layer displays physical hazard. Our machine learning model assesses burn probability using strictly environmental inputs: fuel vegetation, slope, wind, and aridity—with zero demographic features.  
  When we overlay market premiums, disparities appear. By activating our Econometric Audit layer, the map displays residual pricing after controlling for physical hazard, structural home vintage, verified fire mitigation, and coverage amounts across 9,109 California Census tracts."

---

### 3. Census Tract Inspection & Counterfactual Calculator (0:55 – 1:25 | 30s)
* **Screen Action:**  
  Click on a high-disparity Census tract in the Sierra foothill region. The sidebar/detail drawer populates with tract metadata:
  - Median household income quintile: Q1 (lowest)
  - Physical Hazard Score: 0.74
  - Annual Premium: $3,850
  - Unexplained Premium Penalty: +17.4%
  Scroll down to the **"Actuarial Counterfactual Calculator"** slider: toggle "Class A Fire-Resistant Roof" and "100ft Defensible Space". Watch estimated premium recalculate in real-time.
* **Narration:**  
  "Clicking any tract reveals its granular profile. Notice Tract 06017... It faces the exact same 0.74 physical risk score as an affluent coastal-adjacent tract, yet its lowest-income cohort faces an estimated unexplained premium penalty of +17.4%.  
  Below, our property counterfactual calculator empowers homeowners and insurers to simulate hardening ROI—showing that verified clearing and roof hardening can save hundreds of dollars annually."

---

### 4. Risk vs. Premium Scatter & Disparity Analysis (1:25 – 1:55 | 30s)
* **Screen Action:**  
  Scroll to the **"Risk vs. Premium Disparity Scatter"** section. Hover over dots grouped and colored by Income Quintile (Q1 dark red, Q5 light blue). Point cursor to the diverging trendlines where Q1 sits consistently above Q5 for identical physical hazard values.
* **Narration:**  
  "This scatter plot proves why simple correlation fails. For any given level of physical risk along the horizontal axis, lowest-income tracts in Q1 consistently pay more than wealthy tracts in Q5.  
  Crucially, policy non-renewals also show a 2.01x disparity ratio between the lowest and highest income quintiles. Our audit separates risk-justified costs from unexplained market penalties."

---

### 5. Audit Recovery & Placebo Validation (1:55 – 2:25 | 30s)
* **Screen Action:**  
  Navigate to the **"Statistical Validation & Trust"** tab.
  1. Highlight the **Planted-Gap Recovery** card: Planted: `+0.150` vs. Recovered: `+0.160` (95% CI: `[0.126, 0.194]`).
  2. Highlight the **500-Run Income Placebo Test** distribution histogram: Mean gap: `+0.04%`, False positive rate: `5.8%`.
  3. Show Temporal Test AUC: `0.720`, Brier Skill: `+0.019`, and Proxy Leakage R²: `-0.007`.
* **Narration:**  
  "To trust an equity audit, you must prove it doesn't hallucinate bias.  
  In benchmark validation with a planted penalty of +0.150 log points, our econometric model accurately recovered +0.160, safely within the 95% confidence interval of 0.126 to 0.194.  
  Furthermore, we ran a 500-iteration randomized income placebo test: the false disparity averaged just +0.04% with a 5.8% false-positive rate, matching pure statistical noise. Our risk model achieves a temporal AUC of 0.720 on unseen future fire seasons."

---

### 6. IBM LinuxONE Execution & Production Architecture (2:25 – 2:45 | 20s)
* **Screen Action:**  
  Switch window to a terminal terminal/screenshot showing:
  - Command: `uname -m` showing `s390x` (or test execution logs on LinuxONE VM).
  - Output of `python run_all.py` writing SHA-256 governance factsheets.
  - Display slide 8 diagram showing: *Ran on LinuxONE VM* vs. *Enterprise Production Path*.
* **Narration:**  
  "We tested and executed our full data pipeline on an IBM LinuxONE virtual machine, validating high-throughput scoring with IBM Snap ML.  
  For enterprise deployment, our architecture keeps sensitive policyholder data securely inside IBM Db2 for z/OS, scores transactions with microsecond latency on the IBM Telum AI coprocessor via ONNX, and logs tamper-evident compliance records into watsonx.governance."

---

### 7. Close & Impact (2:45 – 3:00 | 15s)
* **Screen Action:**  
  Switch back to the Streamlit app header and display the GitHub repository URL (`https://github.com/thor11223344/Flare-AI`) and Team Thor credits.
* **Narration:**  
  "Two neighborhoods, identical physical fire risk. One pays more. Wildfire Equity Map provides the transparency insurance commissioners, carriers, and communities need to build an equitable climate future.  
  The full open-source codebase is available on GitHub. Thank you."
