import gzip
import csv
import json

INPUT_FILE = "variant_summary.txt.gz"
OUTPUT_FILE = "clinvar_filtered.json"

KEEP_SIGNIFICANCE = {
    "Pathogenic",
    "Likely pathogenic",
    "Pathogenic/Likely pathogenic"
}

KEEP_REVIEW_STATUS = {
    "criteria provided, multiple submitters, no conflicts",
    "criteria provided, single submitter",
    "reviewed by expert panel",
    "practice guideline"
}

KEEP_ASSEMBLY = "GRCh38"

results = []
skipped = 0
kept = 0

with gzip.open(INPUT_FILE, "rt", encoding="utf-8") as f:
    reader = csv.DictReader(f, delimiter="\t")
    for row in reader:
        if row.get("Assembly") != KEEP_ASSEMBLY:
            skipped += 1
            continue
        significance = row.get("ClinicalSignificance", "")
        if not any(sig in significance for sig in KEEP_SIGNIFICANCE):
            skipped += 1
            continue
        review = row.get("ReviewStatus", "")
        if review not in KEEP_REVIEW_STATUS:
            skipped += 1
            continue
        disease = row.get("PhenotypeList", "")
        if not disease or disease in ("not provided", "not specified", "-"):
            skipped += 1
            continue

        results.append({
            "variant_id":       row.get("VariationID"),
            "name":             row.get("Name"),
            "gene":             row.get("GeneSymbol"),
            "significance":     row.get("ClinicalSignificance"),
            "review_status":    row.get("ReviewStatus"),
            "condition":        row.get("PhenotypeList"),
            "condition_db_ids": row.get("PhenotypeIDS"),
            "variant_type":     row.get("Type"),
            "chromosome":       row.get("Chromosome"),
            "assembly":         row.get("Assembly"),
            "omim_ids":         row.get("OtherIDs"),
        })
        kept += 1

        if (kept + skipped) % 100000 == 0:
            print(f"Processed {kept + skipped} rows — kept {kept}, skipped {skipped}")

print(f"\nDone. Kept {kept} variants, skipped {skipped}")
print(f"Saving to {OUTPUT_FILE}...")

with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
    json.dump(results, out, indent=2)

print("Saved.")