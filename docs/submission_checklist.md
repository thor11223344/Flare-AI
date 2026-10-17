# IBM Z Datathon 2026 — Final Submission Checklist
**Team:** Thor  
**Track:** Wildcard (Beyond the Obvious)  
**Project:** Wildfire Equity Map  
**Repository:** [https://github.com/thor11223344/Flare-AI](https://github.com/thor11223344/Flare-AI)  

---

## 1. Public Repository & Security Audit
- [x] **Public Visibility:** Confirm repo is set to **Public** under GitHub Settings -> General -> Danger Zone -> Change repository visibility.
- [x] **Secrets Hygiene:** Verify no secrets, API tokens, or `.env` files are tracked in git. (Only `.env.example` is committed).
- [x] **README Verification:** Confirm `README.md` renders properly on GitHub:
  - Header and badges display correctly.
  - Transparent disclosures state underwriting data and demographics are synthetic, hand-parameterized placeholders on real Census tract boundaries (`cb_2022_06_tract_500k`).
  - Strict separation between "Ran on LinuxONE VM" vs. "Production path (not tested)" is clearly documented.
  - Table showing real vs. synthetic placeholder tract counts (9,109 California Census tracts).
  - AI pair programming disclosure (developed with Antigravity AI coding tools).

---

## 2. LinuxONE VM Verification Screenshot (Slide 8)
- [ ] **Run on LinuxONE VM:** SSH into the IBM LinuxONE Community Cloud VM or Google Colab bridge (`notebooks/deploy_to_ibm_linuxone.ipynb`).
- [ ] **Capture Terminal Output:**
  ```bash
  uname -m
  python run_all.py --no-app
  ```
  *(Expected `uname -m`: `s390x`)*
- [ ] **Insert into Slide 8:**
  - Open `docs/WildfireEquityMap_Deck.pptx`.
  - In Slide 8, replace the labeled cyan box (`INSERT VM SCREENSHOT (uname -m + output)`) with the captured terminal screenshot.
  - Save the updated presentation.

---

## 3. Deck Export (PPTX & PDF)
- [x] **PPTX Generation:** Built via `scripts/build_deck.py` -> `docs/WildfireEquityMap_Deck.pptx` (11 slides, 16:9 widescreen, all slide faces <= 40 words, speaker notes on every slide, exact metrics dynamically loaded from `data/*.json`).
- [ ] **Export to PDF:**
  - Because LibreOffice is not installed on this local build host, open `docs/WildfireEquityMap_Deck.pptx` in Microsoft PowerPoint, Google Slides, or Apple Keynote.
  - Click **File -> Export -> Create PDF/XPS** or **File -> Download -> PDF Document (.pdf)**.
  - Save as `docs/WildfireEquityMap_Deck.pdf`.
  - Verify that all 11 slides render with high contrast and proper text alignment.

---

## 4. Project Description Submission
- [x] **Text Ready:** Verified in `docs/project_description.md` (205 words, within 200–250 word requirement).
- [x] **Dynamically Generated:** Values generated via `scripts/build_description.py` matching `audit_results.json` and `risk_metrics.json`.
- [ ] **Copy & Paste:** Copy the contents of `docs/project_description.md` directly into the Hack2Skill submission form's "Project Summary / Description" field.

---

## 5. Demo Video Recording
- [x] **Video Script:** Completed in `docs/demo_video_script.md` (3:00 target duration).
- [ ] **Record Screen Demo:**
  - Launch Streamlit locally: `streamlit run app/streamlit_app.py`.
  - Follow the 7 timestamped segments in `docs/demo_video_script.md`:
    1. `0:00 - 0:25`: Hook & problem framing
    2. `0:25 - 0:55`: Map layers (Physical Hazard vs. Quoted Premium vs. Unexplained Gap)
    3. `0:55 - 1:25`: Tract detail inspection & property counterfactual calculator
    4. `1:25 - 1:55`: Risk vs. Premium scatter plot & non-renewal disparity
    5. `1:55 - 2:25`: Planted-gap recovery & 500-run placebo audit validation
    6. `2:25 - 2:45`: IBM LinuxONE VM terminal screenshot & enterprise production path
    7. `2:45 - 3:00`: Close & GitHub repo link
- [ ] **Upload Video:** Upload MP4 to YouTube (Unlisted) or Google Drive (public view link) as required by Hack2Skill.

---

## 6. Hack2Skill Final Submission Portal
- [ ] **Submission Deadline:** Confirm exact Day 2 closing time with team leads on the Hack2Skill portal.
- [ ] **Form Inputs:**
  - **Project Title:** Wildfire Equity Map
  - **Track:** Wildcard (Beyond the Obvious)
  - **GitHub URL:** `https://github.com/thor11223344/Flare-AI`
  - **Demo Video URL:** *(Link from Step 5)*
  - **Pitch Deck:** Upload `WildfireEquityMap_Deck.pptx` AND `WildfireEquityMap_Deck.pdf`
  - **Project Description:** Paste text from `docs/project_description.md`
- [ ] **Submit:** Submit before the countdown timer expires.
