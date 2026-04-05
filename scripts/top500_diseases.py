import json
import os

# ── PATHS ─────────────────────────────────────────────────────────────────────
PRODUCT1 = "datas/orpha_json/en_product1.json"
PRODUCT4 = "datas/orpha_json/en_product4.json"
PRODUCT6 = "datas/orpha_json/en_product6.json"
PRODUCT9 = "datas/orpha_json/en_product9_ages.json"
OUTPUT   = "datas/orpha_json/top500_diseases.json"
TOP_N    = 500
# ──────────────────────────────────────────────────────────────────────────────

# Prevalence class → numeric score (higher = more common = higher priority)
PREVALENCE_SCORES = {
    "1-5 / 10 000":          40,
    "1-9 / 100 000":         35,
    "6-9 / 10 000":          38,
    "1-9 / 10 000":          37,
    "1 / 1 000":             42,
    "1-5 / 1 000":           42,
    "1-9 / 1 000":           40,
    "1 / 10 000":            36,
    "1 / 100 000":           30,
    "1-9 / 1 000 000":       15,
    "1 / 1 000 000":         10,
    "<1 / 1 000 000":         5,
    "Unknown":                0,
    "Not yet documented":     0,
}


def load_ndjson(path):
    """Load Orphanet NDJSON — skips index lines."""
    records = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "index" in obj or "_index" in obj:
                continue
            code = str(obj.get("ORPHAcode", "")).strip()
            if code:
                records[code] = obj
    return records


print("Loading Orphanet files...")
p1 = load_ndjson(PRODUCT1)
p4 = load_ndjson(PRODUCT4)
p6 = load_ndjson(PRODUCT6)
p9 = load_ndjson(PRODUCT9)

print(f"  product1: {len(p1)} records")
print(f"  product4: {len(p4)} records")
print(f"  product6: {len(p6)} records")
print(f"  product9: {len(p9)} records")

# Build set of codes that have HPO symptoms (product4)
codes_with_hpo  = set(p4.keys())

# Build set of codes that have gene associations (product6)
codes_with_genes = set(p6.keys())


def score_disease(code, record):
    """
    Score a disease record across 5 signals.
    Returns (total_score, score_breakdown_dict)
    """
    breakdown = {}

    # Signal 1 — Prevalence (0–42 pts)
    prev_score = 0
    p9_rec = p9.get(code, {})
    prevalence_list = p9_rec.get("AverageAgeOfOnset") or []
    # product9 also carries PrevalenceClass in some versions
    prev_class = p9_rec.get("PrevalenceClass", "Unknown") or "Unknown"
    prev_score = PREVALENCE_SCORES.get(prev_class, 0)
    # If no prevalence class but has onset data — give partial credit
    if prev_score == 0 and prevalence_list:
        prev_score = 10
    breakdown["prevalence"] = prev_score

    # Signal 2 — Has definition (0 or 20 pts)
    summary = record.get("SummaryInformation") or []
    has_def = bool(summary and summary[0].get("Definition", "").strip())
    breakdown["has_definition"] = 20 if has_def else 0

    # Signal 3 — Has gene associations (0 or 15 pts)
    breakdown["has_genes"] = 15 if code in codes_with_genes else 0

    # Signal 4 — Has HPO symptom annotations (0 or 15 pts)
    breakdown["has_hpo"] = 15 if code in codes_with_hpo else 0

    # Signal 5 — Has OMIM cross-reference (0 or 10 pts)
    refs = record.get("ExternalReference") or []
    has_omim = any(r.get("Source") == "OMIM" for r in refs)
    breakdown["has_omim"] = 10 if has_omim else 0

    total = sum(breakdown.values())
    return total, breakdown


# Score every disease in product1
print("\nScoring all diseases...")
scored = []
for code, record in p1.items():
    # Only consider actual diseases — skip groups and subtypes
    if record.get("Typology") != "Disease":
        continue

    total, breakdown = score_disease(code, record)
    scored.append({
        "orphacode":  code,
        "name":       record.get("Preferred term", ""),
        "score":      total,
        "breakdown":  breakdown,
    })

# Sort by score descending
scored.sort(key=lambda x: x["score"], reverse=True)

print(f"Total scoreable diseases: {len(scored)}")
print(f"Selecting top {TOP_N}...")

top500 = scored[:TOP_N]

# Show score distribution
print(f"\nTop {TOP_N} diseases selected.")

avg_score = sum(d["score"] for d in top500) / len(top500)
print(f"Average score: {avg_score:.2f}")

print("\nTop 5 diseases:")
for d in top500[:5]:
    print(f"  [{d['score']}] {d['name']}")

print("\nCutoff (last 5 in top 500):")
for d in top500[-5:]:
    print(f"  [{d['score']}] {d['name']}")

print(f"\nTop 10 highest-scored diseases:")
for d in top500[:10]:
    b = d["breakdown"]
    print(f"  [{d['score']:>3}] {d['name']}")
    print(f"        prev:{b['prevalence']} def:{b['has_definition']} "
          f"genes:{b['has_genes']} hpo:{b['has_hpo']} omim:{b['has_omim']}")

print(f"\nBottom 5 of top {TOP_N} (cutoff zone):")
for d in top500[-5:]:
    print(f"  [{d['score']:>3}] {d['name']}")

# Save just the names + codes for the PubMed fetch script
output_data = [{"orphacode": d["orphacode"], "name": d["name"], "score": d["score"]}
               for d in top500]

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(output_data, f, indent=2)

print(f"\nSaved {len(output_data)} re-ranked diseases to {OUTPUT}")