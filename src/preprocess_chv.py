import csv
import json
from pathlib import Path

RAW_DIR = Path(__file__).parent.parent / "data" / "raw" / "chv"
OUT_PATH = Path(__file__).parent.parent / "data" / "processed" / "chv_lookup.json"

def build_lookup():
    lookup = {}
    infile = RAW_DIR / "CHV_concepts_terms_flatfile_20110204.tsv"
    fieldnames = [
        "CUI",
        "Term",
        "CHV Preferred Name",
        "UMLS Preferred Name",
        "Explanation",
        "UMLS preferred",
        "CHV preferred",
        "Disparaged",
        "Frequency Score",
        "Context Score",
        "CUI Score",
        "Combo Score",
        "Combo Score - No top words",
        "CHV String ID",
        "CHV Concept ID"
    ]
    with infile.open(newline="", encoding="utf-8") as tsv:
        reader = csv.DictReader(tsv, delimiter="\t", fieldnames=fieldnames)
        for row in reader:
            # Skip misspelled or abnormal entries
            if row["Disparaged"].strip().lower() == "yes":
                continue
            consumer = row["Term"].strip().lower()
            standard = row["UMLS Preferred Name"].strip().lower()
            cui = row["CUI"].strip()
            if consumer and standard:
                lookup[consumer] = {"standard_term": standard, "CUI": cui}

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as out:
        json.dump(lookup, out, indent=2, ensure_ascii=False)
    print(f"Wrote {len(lookup)} entries to {OUT_PATH}")

if __name__ == "__main__":
    build_lookup()