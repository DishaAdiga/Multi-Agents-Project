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

# ── STORE 1: Disease store (all 11k diseases) 
print("\nBuilding disease store...")
diseases = build_unified_records(
    PATHS["product1"], PATHS["product4"], PATHS["product6"],
    PATHS["product9"], PATHS["hp"], PATHS["pubmed"]
)

# Only embed diseases with at least some content
valid = [d for d in diseases.values() if d["rag_text"].strip()]
texts = [d["rag_text"] for d in valid]
meta  = [{"orphacode": d["orphacode"], "name": d["name"]} for d in valid]

print(f"Embedding {len(texts)} disease records...")
vectors = model.encode(texts, batch_size=64, show_progress_bar=True)
index = faiss.IndexFlatL2(vectors.shape[1])
index.add(np.array(vectors))
faiss.write_index(index, "rag/stores/disease.index")
with open("rag/stores/disease_meta.json", "w") as f:
    json.dump({"records": meta, "texts": texts}, f)
print(f"Disease store: {index.ntotal} vectors saved")

# ── STORE 2: Case report store (701 diseases with abstracts) 
print("\nBuilding case report store...")
case_texts = []
case_meta  = []
for d in diseases.values():
    for ab in d.get("abstracts", []):
        text = f"Disease: {d['name']}\nCase report: {ab.get('abstract','')}"
        case_texts.append(text)
        case_meta.append({
            "orphacode": d["orphacode"],
            "name":      d["name"],
            "pmid":      ab.get("pmid",""),
            "pub_year":  ab.get("pub_year",""),
            "authors":   ab.get("authors",[]),
            "journal":   ab.get("journal",""),
        })

print(f"Embedding {len(case_texts)} case reports...")
case_vectors = model.encode(case_texts, batch_size=64, show_progress_bar=True)
case_index = faiss.IndexFlatL2(case_vectors.shape[1])
case_index.add(np.array(case_vectors))
faiss.write_index(case_index, "rag/stores/cases.index")
with open("rag/stores/cases_meta.json", "w") as f:
    json.dump({"records": case_meta, "texts": case_texts}, f)
print(f"Case store: {case_index.ntotal} vectors saved")

# ── STORE 3: Genetics store (ClinVar) 
print("\nBuilding genetics store...")
gene_to_variants, _ = parse_clinvar(PATHS["clinvar"])
genetics_texts = []
genetics_meta  = []
for gene, variants in gene_to_variants.items():
    # Group all variants per gene into one chunk
    conditions = list({v["condition"].split("|")[0].strip()
                       for v in variants if v["condition"]})[:5]
    text = (f"Gene: {gene}\n"
            f"Associated conditions: {', '.join(conditions)}\n"
            f"Pathogenic variants: {len(variants)}\n"
            f"Significance: {variants[0]['significance']}")
    genetics_texts.append(text)
    genetics_meta.append({"gene": gene, "variant_count": len(variants),
                           "conditions": conditions})

print(f"Embedding {len(genetics_texts)} gene records...")
gen_vectors = model.encode(genetics_texts, batch_size=64, show_progress_bar=True)
gen_index = faiss.IndexFlatL2(gen_vectors.shape[1])
gen_index.add(np.array(gen_vectors))
faiss.write_index(gen_index, "rag/stores/genetics.index")
with open("rag/stores/genetics_meta.json", "w") as f:
    json.dump({"records": genetics_meta, "texts": genetics_texts}, f)
print(f"Genetics store: {gen_index.ntotal} vectors saved")

# ── STORE 4: Lab store
print("\nBuilding lab store...")
with open(PATHS["lab"], encoding="utf-8") as f:
    lab_tests = json.load(f)

lab_texts = []
lab_meta  = []
for test in lab_tests:
    text = (f"Test: {test['test']} ({test.get('abbreviation','')})\n"
            f"Panel: {test.get('panel','')}\n"
            f"Normal range: {test.get('normal_range',{})}\n"
            f"Low means: {test.get('low_flag','')}\n"
            f"High means: {test.get('high_flag','')}\n"
            f"Relevant diseases: {', '.join(test.get('relevant_rare_diseases',[]))}")
    lab_texts.append(text)
    lab_meta.append({"test": test["test"],
                     "abbreviation": test.get("abbreviation",""),
                     "panel": test.get("panel",""),
                     "normal_range": test.get("normal_range",{}),
                     "critical_low": test.get("critical_low"),
                     "critical_high": test.get("critical_high"),
                     "low_flag": test.get("low_flag",""),
                     "high_flag": test.get("high_flag","")})

lab_vectors = model.encode(lab_texts, batch_size=64, show_progress_bar=True)
lab_index = faiss.IndexFlatL2(lab_vectors.shape[1])
lab_index.add(np.array(lab_vectors))
faiss.write_index(lab_index, "rag/stores/lab.index")
with open("rag/stores/lab_meta.json", "w") as f:
    json.dump({"records": lab_meta, "texts": lab_texts}, f)
print(f"Lab store: {lab_index.ntotal} vectors saved")

# ── VERIFY ALL STORES WITH TEST QUERY 
print("\n── Verifying stores with test queries ────────────────")

def search(index_path, meta_path, query, k=3):
    idx  = faiss.read_index(index_path)
    with open(meta_path) as f:
        meta_data = json.load(f)
    q_vec = model.encode([query])
    _, indices = idx.search(np.array(q_vec), k)
    return [meta_data["records"][i] for i in indices[0] if i < len(meta_data["records"])]

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