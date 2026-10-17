"""Creates a clean zip archive of FLare-AI excluding virtual environments and caches,
ready to be uploaded to Google Colab or transferred via SCP to IBM LinuxONE.
"""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_ZIP = ROOT / "flare_ai_project.zip"

EXCLUDE_DIRS = {
    ".venv", "venv", "env", "__pycache__", ".pytest_cache", ".git", ".idea", ".vscode"
}
EXCLUDE_EXTS = {".pyc", ".pyd", ".pyo", ".zip"}

def create_archive():
    print(f"Creating clean archive at: {OUT_ZIP}")
    file_count = 0
    with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in ROOT.rglob("*"):
            # Skip excluded dirs
            if any(part in EXCLUDE_DIRS for part in p.parts):
                continue
            if p.is_file() and p.suffix not in EXCLUDE_EXTS:
                arcname = p.relative_to(ROOT)
                zf.write(p, arcname)
                file_count += 1
    print(f"[+] Successfully archived {file_count} files into {OUT_ZIP.name} ({OUT_ZIP.stat().st_size / (1024*1024):.2f} MB)")

if __name__ == "__main__":
    create_archive()
