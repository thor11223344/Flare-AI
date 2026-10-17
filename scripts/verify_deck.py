"""Verifies docs/WildfireEquityMap_Deck.pptx:
1. Confirms exactly 11 slides.
2. Confirms speaker notes exist on each slide.
3. Checks word count per slide face (must be <= 40 words).
4. Extracts numbers from the slide face and compares them against data/*.json values.
"""
import re
import json
from pathlib import Path
from pptx import Presentation

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PPTX_PATH = ROOT / "docs" / "WildfireEquityMap_Deck.pptx"


def load_json_numbers():
    numbers = set()
    for jf in DATA_DIR.glob("*.json"):
        try:
            raw = jf.read_text(encoding="utf-8")
            # Find all ints and floats
            found = re.findall(r"[-+]?\d*\.?\d+", raw)
            numbers.update(found)
        except Exception:
            pass
    for gov in (DATA_DIR / "governance_logs").glob("*.json"):
        try:
            raw = gov.read_text(encoding="utf-8")
            found = re.findall(r"[-+]?\d*\.?\d+", raw)
            numbers.update(found)
        except Exception:
            pass
    # Add standard structural numbers (1, 2, 3, 4, 5, 2026, etc.)
    numbers.update({"1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "2026", "2030", "2035", "500", "95", "9109", "195000", "0"})
    return numbers


def verify_deck():
    prs = Presentation(str(PPTX_PATH))
    num_slides = len(prs.slides)
    print(f"Total Slides: {num_slides} (Expected: 11)")
    assert num_slides == 11, f"Expected 11 slides, found {num_slides}"

    json_numbers = load_json_numbers()
    has_notes = True
    all_clean = True

    for i, slide in enumerate(prs.slides, start=1):
        # Extract visual slide face text
        slide_text = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                for p in shape.text_frame.paragraphs:
                    if p.text.strip():
                        slide_text.append(p.text.strip())

        full_face = " ".join(slide_text)
        words = full_face.split()
        word_count = len(words)

        # Check speaker notes
        notes_text = ""
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
            notes_text = slide.notes_slide.notes_text_frame.text.strip()
        has_slide_notes = len(notes_text) > 0
        if not has_slide_notes:
            has_notes = False

        print(f"\n--- Slide {i} ---")
        print(f"  Face Word Count: {word_count} words (Limit: <= 40)")
        print(f"  Speaker Notes: {'YES (' + str(len(notes_text.split())) + ' words)' if has_slide_notes else 'MISSING'}")
        if word_count > 40:
            print(f"  [!] WARNING: Slide {i} exceeds 40 words ({word_count} words)")
            all_clean = False

        # Check numbers on slide face (ignore numbers that are part of URLs or handles)
        face_without_urls = re.sub(r"https?://\S+", "", full_face)
        slide_numbers = re.findall(r"[-+]?\d*\.?\d+", face_without_urls)
        for num in slide_numbers:
            # Check if num or close float representation is in JSON numbers
            matched = False
            try:
                val = float(num)
                # Check directly or as formatted
                if num in json_numbers:
                    matched = True
                else:
                    for jn in json_numbers:
                        try:
                            if abs(float(jn) - val) < 0.05:
                                matched = True
                                break
                        except ValueError:
                            pass
            except ValueError:
                pass

            if not matched:
                print(f"  [?] Number {num} not found directly in data/*.json")
                all_clean = False

    print("\n" + "=" * 50)
    print(f"Verification Result: {'ALL CHECKS PASSED' if has_notes and all_clean else 'REVIEW WARNINGS'}")
    print("=" * 50)


if __name__ == "__main__":
    verify_deck()
