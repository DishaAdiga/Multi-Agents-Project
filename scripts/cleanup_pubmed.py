import json

INPUT  = "datas/rare_disease_abstracts.json"
OUTPUT = "datas/rare_disease_abstracts.json"  # overwrite in place
RANKED = "datas/orpha_json/top500_diseases.json"

# Load everything
with open(INPUT, encoding="utf-8") as f:
    abstracts = json.load(f)

with open(RANKED, encoding="utf-8") as f:
    ranked = json.load(f)

# Build ranked order lookup
ranked_order = {d["orphacode"]: i for i, d in enumerate(ranked)}

# Sort — re-ranked diseases first, extras at the end
def sort_key(record):
    code = record.get("orphacode", "")
    # if in ranked list → use its rank position
    # if not → put at end (999999)
    return ranked_order.get(code, 999999)

abstracts.sort(key=sort_key)

# Stats
in_ranked     = sum(1 for r in abstracts if r["orphacode"] in ranked_order)
not_in_ranked = len(abstracts) - in_ranked
with_abstracts = sum(1 for r in abstracts if r.get("abstracts"))
total_abstracts = sum(len(r.get("abstracts", [])) for r in abstracts)

print(f"Total disease records  : {len(abstracts)}")
print(f"  From re-ranked list  : {in_ranked}")
print(f"  Bonus from yesterday : {not_in_ranked}")
print(f"With abstracts         : {with_abstracts}")
print(f"Total abstracts        : {total_abstracts}")
print(f"Avg abstracts/disease  : {total_abstracts/with_abstracts:.1f}")

# Save sorted
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(abstracts, f, indent=2, ensure_ascii=False)

print(f"\nSaved sorted file to {OUTPUT}")
print("First 5 diseases (should be highest-scored):")
for r in abstracts[:5]:
    n_abs = len(r.get("abstracts", []))
    print(f"  [{r['orphacode']}] {r['disease']} — {n_abs} abstracts")

print("\nLast 5 diseases (yesterday's extras):")
for r in abstracts[-5:]:
    n_abs = len(r.get("abstracts", []))
    print(f"  [{r['orphacode']}] {r['disease']} — {n_abs} abstracts")