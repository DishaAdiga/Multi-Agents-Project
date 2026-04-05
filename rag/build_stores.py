import json
import faiss
import numpy as np
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sentence_transformers import SentenceTransformer
from utils.parsers import build_unified_records, parse_clinvar

os.makedirs("rag/stores", exist_ok=True)

PATHS = {
    "product1": "../datas/orpha_json/en_product1.json",
    "product4": "../datas/orpha_json/en_product4.json",
    "product6": "../datas/orpha_json/en_product6.json",
    "product9": "../datas/orpha_json/en_product9_ages.json",
    "hp":       "../datas/hp.json",
    "pubmed":   "../datas/rare_disease_abstracts.json",
    "clinvar":  "../datas/clinvar_filtered.json",
    "lab":      "../datas/lab_reference.json",
}

print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")


# ─────────────────────────────────────────────────────────────
# STORE 1: DISEASE STORE
# ─────────────────────────────────────────────────────────────
print("\nBuilding disease store...")

diseases = build_unified_records(
    PATHS["product1"], PATHS["product4"], PATHS["product6"],
    PATHS["product9"], PATHS["hp"], PATHS["pubmed"]
)

valid = [
    d for d in diseases.values()
    if d["rag_text"].strip()
    and not d["name"].lower().startswith("obsolete")
]

texts = [d["rag_text"] for d in valid]
meta  = [{"orphacode": d["orphacode"], "name": d["name"]} for d in valid]

print(f"Embedding {len(texts)} disease records...")
vectors = np.array(model.encode(texts, batch_size=64, show_progress_bar=True)).astype("float32")
faiss.normalize_L2(vectors)

index = faiss.IndexFlatIP(vectors.shape[1])
index.add(vectors)

faiss.write_index(index, "rag/stores/disease.index")

with open("rag/stores/disease_meta.json", "w") as f:
    json.dump({"records": meta, "texts": texts}, f)

print(f"Disease store: {index.ntotal} vectors saved")


# ─────────────────────────────────────────────────────────────
# STORE 2: CASE REPORT STORE
# ─────────────────────────────────────────────────────────────
print("\nBuilding case report store...")

case_texts = []
case_meta  = []
seen_pmids = set()

for d in diseases.values():
    for ab in d.get("abstracts", []):

        title    = ab.get("title", "").strip()
        abstract = ab.get("abstract", "").strip()
        journal  = ab.get("journal", "").strip()
        year     = ab.get("pub_year", "")
        pmid     = ab.get("pmid", "")

        if not abstract or not pmid:
            continue

        if pmid in seen_pmids:
            continue

        seen_pmids.add(pmid)

        text = (
            f"Primary disease: {d['name']}\n"
            f"Title: {title}\n"
            f"Journal: {journal} ({year})\n"
            f"Abstract: {abstract}"
        )

        case_texts.append(text)
        case_meta.append({
            "orphacode": d["orphacode"],
            "name":      d["name"],
            "pmid":      pmid,
            "pub_year":  year,
            "authors":   ab.get("authors", []),
            "journal":   journal,
            "title":     title,
        })

print(f"Embedding {len(case_texts)} case reports...")
case_vectors = np.array(model.encode(case_texts, batch_size=64, show_progress_bar=True)).astype("float32")
faiss.normalize_L2(case_vectors)

case_index = faiss.IndexFlatIP(case_vectors.shape[1])
case_index.add(case_vectors)

faiss.write_index(case_index, "rag/stores/cases.index")

with open("rag/stores/cases_meta.json", "w") as f:
    json.dump({"records": case_meta, "texts": case_texts}, f)

print(f"Case store: {case_index.ntotal} vectors saved")


# ─────────────────────────────────────────────────────────────
# STORE 3: GENETICS STORE (CLEANED)
# ─────────────────────────────────────────────────────────────
print("\nBuilding genetics store...")

gene_to_variants, _ = parse_clinvar(PATHS["clinvar"])

def is_valid_gene(gene):
    gene = gene.strip().lower()
    if not gene:
        return False
    if "subset" in gene:
        return False
    if ":" in gene or ";" in gene:
        return False
    if len(gene) > 15:
        return False
    return True

def is_valid_condition(cond):
    if not cond:
        return False
    cond = cond.lower()
    bad = ["not provided", "not specified", "see cases", "-"]
    return cond not in bad

genetics_texts = []
genetics_meta  = []

for gene, variants in gene_to_variants.items():

    if not is_valid_gene(gene):
        continue

    unique_variants = {v["variant_id"]: v for v in variants}
    variants = list(unique_variants.values())

    conditions = list({
        v["condition"].split("|")[0].strip()
        for v in variants
        if is_valid_condition(v.get("condition"))
    })[:5]

    if not conditions:
        continue

    text = (
        f"Gene: {gene}\n"
        f"Diseases: {', '.join(conditions)}\n"
        f"Variant count: {len(variants)}\n"
        f"Pathogenic variants"
    )

    genetics_texts.append(text)
    genetics_meta.append({
        "gene": gene,
        "variant_count": len(variants),
        "conditions": conditions
    })

print(f"Embedding {len(genetics_texts)} gene records...")
gen_vectors = np.array(model.encode(genetics_texts, batch_size=64, show_progress_bar=True)).astype("float32")
faiss.normalize_L2(gen_vectors)

gen_index = faiss.IndexFlatIP(gen_vectors.shape[1])
gen_index.add(gen_vectors)

faiss.write_index(gen_index, "rag/stores/genetics.index")

with open("rag/stores/genetics_meta.json", "w") as f:
    json.dump({"records": genetics_meta, "texts": genetics_texts}, f)

print(f"Genetics store: {gen_index.ntotal} vectors saved")


# ─────────────────────────────────────────────────────────────
# STORE 4: LAB STORE
# ─────────────────────────────────────────────────────────────
print("\nBuilding lab store...")

with open(PATHS["lab"], encoding="utf-8") as f:
    lab_tests = json.load(f)

lab_texts = []
lab_meta  = []

for test in lab_tests:
    text = (
        f"{test['test']} indicates {test.get('high_flag','')} "
        f"Related to {', '.join(test.get('relevant_rare_diseases',[]))}"
    )

    lab_texts.append(text)
    lab_meta.append({
        "test": test["test"],
        "abbreviation": test.get("abbreviation",""),
        "panel": test.get("panel",""),
        "normal_range": test.get("normal_range",{}),
        "low_flag": test.get("low_flag",""),
        "high_flag": test.get("high_flag","")
    })

lab_vectors = np.array(model.encode(lab_texts, batch_size=64, show_progress_bar=True)).astype("float32")
faiss.normalize_L2(lab_vectors)

lab_index = faiss.IndexFlatIP(lab_vectors.shape[1])
lab_index.add(lab_vectors)

faiss.write_index(lab_index, "rag/stores/lab.index")

with open("rag/stores/lab_meta.json", "w") as f:
    json.dump({"records": lab_meta, "texts": lab_texts}, f)

print(f"Lab store: {lab_index.ntotal} vectors saved")


# ─────────────────────────────────────────────────────────────
# SEARCH FUNCTION (DEDUP + COSINE)
# ─────────────────────────────────────────────────────────────

def make_hashable(d):
    out = []
    for k, v in d.items():
        if isinstance(v, list):
            v = tuple(v)
        elif isinstance(v, dict):
            v = tuple(sorted(v.items()))
        out.append((k, v))
    return tuple(sorted(out))

def search(index_path, meta_path, query, k=3):
    idx = faiss.read_index(index_path)

    with open(meta_path) as f:
        meta_data = json.load(f)

    q_vec = np.array(model.encode([query])).astype("float32")
    faiss.normalize_L2(q_vec)

    _, indices = idx.search(q_vec, k * 2)

    seen = set()
    results = []

    for i in indices[0]:
        if i >= len(meta_data["records"]):
            continue

        r = meta_data["records"][i]
        key = make_hashable(r)

        if key in seen:
            continue

        seen.add(key)
        results.append(r)

        if len(results) == k:
            break

    return results


# ─────────────────────────────────────────────────────────────
# VERIFICATION
# ─────────────────────────────────────────────────────────────
print("\n── Verifying stores with test queries ────────────────")

print("\nQuery: 'muscle weakness and respiratory failure'")
for r in search("rag/stores/disease.index", "rag/stores/disease_meta.json",
                "muscle weakness and respiratory failure"):
    print(f"  -> {r['name']} (OrphaCode: {r['orphacode']})")

print("\nQuery: 'GAA gene pathogenic variant'")
for r in search("rag/stores/genetics.index", "rag/stores/genetics_meta.json",
                "GAA gene pathogenic variant"):
    print(f"  -> Gene: {r['gene']} | Conditions: {r['conditions'][:2]}")

print("\nQuery: 'elevated creatine kinase muscle damage'")
for r in search("rag/stores/lab.index", "rag/stores/lab_meta.json",
                "elevated creatine kinase muscle damage"):
    print(f"  -> {r['test']} | High: {r['high_flag'][:60]}")

print("\nPhase 2 complete — all 4 FAISS stores built and verified!")