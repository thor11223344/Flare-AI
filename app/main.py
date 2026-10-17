"""
Main entrypoint for Streamlit application.
"""
from pathlib import Path
import subprocess
import sys

if __name__ == "__main__":
    app_path = Path(__file__).parent / "streamlit_app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)], check=True)
