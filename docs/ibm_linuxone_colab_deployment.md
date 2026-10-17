# IBM LinuxONE Deployment & Acceleration via Google Colab

This guide outlines the division of responsibilities, automation workflows, and step-by-step instructions to upload, configure, and benchmark the **FLare-AI** project on the **IBM LinuxONE (s390x) Community Cloud VM** using Google Colab.

---

## 🛠️ What I Have Already Done For You

1. **Created a Turnkey Google Colab Bridge Notebook:**
   * [`notebooks/deploy_to_ibm_linuxone.ipynb`](../notebooks/deploy_to_ibm_linuxone.ipynb)
   * Handles SSH authentication, codebase deployment (via GitHub clone or direct ZIP upload), environment configuration, `nnpa` hardware flag checks, and remote benchmark execution directly from Google Colab.

2. **Created the IBM Snap ML Hardware Benchmark:**
   * [`src/ibmz/snapml_benchmark.py`](../src/ibmz/snapml_benchmark.py)
   * Evaluates standard Scikit-Learn against IBM Snap ML with `n_jobs=os.cpu_count()`, matching the IBM z16/z17 Telum on-chip AI acceleration configuration from the official reproduction report.

3. **Updated LinuxONE Configuration Files:**
   * Added `snapml>=1.17.0` to [`requirements-ibmz.txt`](../requirements-ibmz.txt).
   * Added `install-ibmz` and `benchmark-ibmz` targets to [`Makefile`](../Makefile).
   * Added dynamic Snap ML fallback in [`src/audit/audit.py`](../src/audit/audit.py) to utilize `snapml.RandomForestRegressor` with explicit thread counts.

4. **Packaged the Project Archive:**
   * Built [`scripts/package_for_upload.py`](../scripts/package_for_upload.py) and generated [`flare_ai_project.zip`](../flare_ai_project.zip) (clean archive excluding `.venv`, cache files, and git history, ready for immediate upload).

---

## 📋 What You Need To Do

You have two workflows depending on how you prefer to use Google Colab:

---

### Option 1: Use Colab as the Deployment & Automation Bridge (Recommended)

In this approach, you run the provided notebook in Google Colab to upload and trigger the project on LinuxONE without touching local command lines.

1. **Open Google Colab:**
   * Go to [colab.research.google.com](https://colab.research.google.com/).
   * Click **Upload** and select [`notebooks/deploy_to_ibm_linuxone.ipynb`](../notebooks/deploy_to_ibm_linuxone.ipynb).

2. **Run Step 1 & 2 (Configure & Authenticate):**
   * Keep the target IP as `148.100.76.172` and user as `linux1`.
   * When prompted in Step 2, upload your SSH private key file (`linuxone_key`).

3. **Deploy Code (Step 4):**
   * **If using Git:** Ensure your latest commits are pushed to GitHub, then run the **GitHub Clone/Pull** cell.
   * **If using Direct Upload:** Select **Upload ZIP from Colab** and upload [`flare_ai_project.zip`](../flare_ai_project.zip).

4. **Execute Steps 5–8 in Colab:**
   * **Step 5:** Automatically installs dependencies with `--break-system-packages` and creates the `snapml` dist-packages symlink.
   * **Step 6:** Confirms hardware flags (`nnpa`).
   * **Step 7:** Runs `snapml_benchmark.py` and outputs the speedup ratio.
   * **Step 8:** Runs `python3 run_all.py --no-app --force`.

---

### Option 2: Connect Colab's UI Directly to the LinuxONE Mainframe

If you want to write and execute code inside Google Colab cells while having them run directly on IBM LinuxONE's s390x hardware:

1. **Verify Jupyter is running on LinuxONE:**
   Ensure the background Jupyter daemon from Section 2 of your report is active:
   ```bash
   nohup jupyter notebook \
     --ip=0.0.0.0 \
     --port=8888 \
     --no-browser \
     --NotebookApp.token='datathon2026' \
     > ~/jupyter.log 2>&1 &
   ```

2. **Open SSH Tunnel from your local machine (Windows PowerShell or Mac):**
   ```powershell
   ssh -i C:\path\to\linuxone_key -N -L 8888:localhost:8888 linux1@148.100.76.172
   ```

3. **Attach Google Colab to LinuxONE:**
   * In Google Colab, look at the top right header next to the **Connect** button.
   * Click the arrow dropdown ▾ next to **Connect** and select **"Connect to a local runtime"**.
   * Enter the backend URL:
     ```text
     http://localhost:8888/?token=datathon2026
     ```
   * Click **Connect**. Your Colab runtime is now directly executing on the IBM LinuxONE mainframe.
