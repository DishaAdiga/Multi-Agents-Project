"""
Retrieval Tools
5 @tool-decorated functions that LangGraph agents call automatically.
FAISS retrieval logic carried over from Phase 2 unchanged.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import faiss
import numpy as np
from langchain.tools import tool
from sentence_transformers import SentenceTransformer

os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent / "rag" / "rag" / "stores"

INDEX_PATHS = {
    "disease":  BASE_DIR / "disease.index",
    "cases":    BASE_DIR / "cases.index",
    "genetics": BASE_DIR / "genetics.index",
    "lab":      BASE_DIR / "lab.index",
}

META_PATHS = {
    "disease":  BASE_DIR / "disease_meta.json",
    "cases":    BASE_DIR / "cases_meta.json",
    "genetics": BASE_DIR / "genetics_meta.json",
    "lab":      BASE_DIR / "lab_meta.json",
}

HPO_DATA_PATH    = Path(__file__).resolve().parent.parent / "datas" / "hp.json"
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

# ---------------------------------------------------------------------------
# Lazy-loaded singletons
# ---------------------------------------------------------------------------

_embedder:  SentenceTransformer | None = None
_indexes:   dict[str, faiss.Index]     = {}
_metas:     dict[str, list[dict]]      = {}
_hpo_terms: list[dict] | None          = None

import threading
_embedder_lock = threading.Lock()

def _get_embedder() -> SentenceTransformer:
    global _embedder
    with _embedder_lock:
        if _embedder is None:
            _embedder = SentenceTransformer(EMBED_MODEL_NAME)
    return _embedder


def _get_index(store: str) -> faiss.Index:
    if store not in _indexes:
        path = INDEX_PATHS[store]
        if not path.exists():
            raise FileNotFoundError(
                f"FAISS index not found: {path}. Run Phase 2 build scripts first."
            )
        _indexes[store] = faiss.read_index(str(path))
    return _indexes[store]


# ---------------------------------------------------------------------------
# Text parsers — extract structured fields from rich text chunks
# ---------------------------------------------------------------------------

def _extract(text: str, label: str) -> str:
    """Pull a single-line field from a text chunk by label."""
    match = re.search(rf"{label}:\s*(.+)", text)
    return match.group(1).strip() if match else "N/A"


def _parse_disease_record(record: dict, text: str) -> dict:
    """
    Enrich a disease record with fields parsed from its text chunk.
    Text format:
        Disease: <name>
        OrphaCode: <code>
        Also known as: <synonyms>
        Description: <text>
        Frequent features: <comma list>
        Occasional features: <comma list>
        Associated genes: <genes>
        Age of onset: <onset>
        Inheritance: <pattern>
        Cross-references: <refs>
    """
    record["synonyms"]    = _extract(text, "Also known as")
    record["description"] = _extract(text, "Description")
    record["inheritance"] = _extract(text, "Inheritance")
    record["onset"]       = _extract(text, "Age of onset")
    record["genes"]       = _extract(text, "Associated genes")

    frequent = _extract(text, "Frequent features")
    record["hpo_terms"] = (
        [f.strip() for f in frequent.split(",") if f.strip()]
        if frequent != "N/A" else []
    )

    occasional = _extract(text, "Occasional features")
    record["occasional_features"] = (
        [f.strip() for f in occasional.split(",") if f.strip()]
        if occasional != "N/A" else []
    )
    return record


def _parse_genetics_record(record: dict, text: str) -> dict:
    """
    Enrich a genetics record from its text chunk.
    Text format:
        Gene: <symbol>
        Diseases: <comma list>
        Variant count: <n>
        Pathogenic variants
    """
    # gene and conditions already in record from Phase 2
    # extract significance from last line
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    record["significance"] = lines[-1] if lines else "N/A"
    return record


def _parse_lab_record(record: dict, text: str) -> dict:
    """
    Enrich a lab record from its text chunk.
    Text format (single line):
        <Test> indicates <condition> — consider <diseases> Related to <diseases>
    """
    # Split on " — " to get high/low flag and disease associations
    parts = text.split(" — ", 1)
    if len(parts) == 2:
        record["high_flag"] = parts[0].strip()
        record["disease_context"] = parts[1].strip()
    else:
        record["high_flag"]       = text.strip()
        record["disease_context"] = "N/A"

    # Parse normal range dict into readable string
    normal = record.get("normal_range", {})
    if isinstance(normal, dict):
        lo = normal.get("min", "?")
        hi = normal.get("max", "?")
        record["normal_range_str"] = f"{lo} – {hi}"
    else:
        record["normal_range_str"] = str(normal)

    return record


# ---------------------------------------------------------------------------
# Meta loader with per-store parsing
# ---------------------------------------------------------------------------

def _get_meta(store: str) -> list[dict]:
    if store not in _metas:
        path = META_PATHS[store]
        if not path.exists():
            raise FileNotFoundError(f"Meta JSON not found: {path}")
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)

        records = raw["records"]
        texts   = raw["texts"]

        parsers = {
            "disease":  _parse_disease_record,
            "genetics": _parse_genetics_record,
            "lab":      _parse_lab_record,
        }

        for record, text in zip(records, texts):
            record["text"] = text
            if store in parsers:
                record = parsers[store](record, text)

        _metas[store] = records
    return _metas[store]


def _get_hpo() -> list[dict]:
    global _hpo_terms
    if _hpo_terms is None:
        _hpo_terms = _load_hpo_terms()
    return _hpo_terms

# ---------------------------------------------------------------------------
# Core FAISS search
# ---------------------------------------------------------------------------

def _faiss_search(store: str, query: str, top_k: int) -> list[dict]:
    embedder = _get_embedder()
    index    = _get_index(store)
    meta     = _get_meta(store)

    vec = embedder.encode([query], normalize_embeddings=True).astype(np.float32)
    distances, indices = index.search(vec, top_k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        idx = int(idx)
        if idx == -1:
            continue
        record = dict(meta[idx])
        record["_score"] = float(dist)
        results.append(record)
    return results

# ---------------------------------------------------------------------------
# Tool 1 — search_disease_profiles
# ---------------------------------------------------------------------------

@tool
def search_disease_profiles(query: str) -> str:
    """
    Search the Orphanet rare disease knowledge base (11,456 diseases) using
    semantic similarity. Use this when the user describes clinical symptoms,
    phenotypes, or mentions a disease name. Returns OrphaCode, disease name,
    synonyms, inheritance pattern, associated genes, age of onset, and
    frequent clinical features.

    Args:
        query: Clinical description of symptoms or disease features.
               Example: 'progressive muscle weakness with respiratory failure in a child'
    """
    try:
        results = _faiss_search("disease", query, top_k=5)
        output  = []
        for r in results:
            output.append({
                "orpha_code":          r.get("orphacode", "N/A"),
                "name":                r.get("name", "Unknown"),
                "synonyms":            r.get("synonyms", "N/A"),
                "description":         r.get("description", "N/A"),
                "inheritance":         r.get("inheritance", "N/A"),
                "onset":               r.get("onset", "N/A"),
                "associated_genes":    r.get("genes", "N/A"),
                "frequent_features":   r.get("hpo_terms", []),
                "occasional_features": r.get("occasional_features", []),
                "similarity":          round(r["_score"], 4),
            })
        return json.dumps(output, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": str(exc)})

# ---------------------------------------------------------------------------
# Tool 2 — search_case_reports
# ---------------------------------------------------------------------------

@tool
def search_case_reports(query: str) -> str:
    """
    Search 1,171 PubMed rare disease case report abstracts using semantic
    similarity. Use this to find real-world precedents, validate a diagnosis
    against published cases, or answer 'has this presentation been reported?'
    Returns PMID, title, abstract excerpt, year, and disease.

    Args:
        query: Clinical scenario to match against case reports.
               Example: 'adult-onset Pompe disease presenting as respiratory failure'
    """
    try:
        results = _faiss_search("cases", query, top_k=3)
        output  = []
        for r in results:
            output.append({
                "pmid":       r.get("pmid", "N/A"),
                "title":      r.get("title", "Untitled"),
                "abstract":   r.get("text", "")[:600],
                "year":       r.get("year", "N/A"),
                "disease":    r.get("disease", "N/A"),
                "similarity": round(r["_score"], 4),
            })
        return json.dumps(output, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": str(exc)})

# ---------------------------------------------------------------------------
# Tool 3 — search_genetic_variants
# ---------------------------------------------------------------------------

@tool
def lookup_genetic_data(query: str) -> str:
    """
    Search ClinVar genetic variant data grouped by gene symbol. Use this when
    the user mentions a gene name, variant notation (e.g. c.925G>A), or asks
    about genetic confirmation of a disease. Returns gene symbol, associated
    conditions, variant count, and clinical significance.

    Args:
        query: Gene symbol, variant notation, or condition name.
               Example: 'GAA gene pathogenic variant Pompe disease'
    """
    try:
        results = _faiss_search("genetics", query, top_k=5)
        output  = []
        for r in results:
            output.append({
                "gene":          r.get("gene", "N/A"),
                "conditions":    r.get("conditions", []),
                "variant_count": r.get("variant_count", "N/A"),
                "significance":  r.get("significance", "N/A"),
                "summary":       r.get("text", "")[:400],
                "similarity":    round(r["_score"], 4),
            })
        return json.dumps(output, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": str(exc)})

# ---------------------------------------------------------------------------
# Tool 4 — check_lab_values
# ---------------------------------------------------------------------------

@tool
def check_lab_values(query: str) -> str:
    """
    Look up laboratory test reference ranges and rare disease associations.
    Covers 35 key tests (CK, LDH, ammonia, alpha-galactosidase, etc.). Use
    this when the user provides lab results or asks what abnormal values indicate.
    Returns normal range, high/low interpretations, and associated diseases.

    Args:
        query: Lab test name or abnormal finding.
               Example: 'elevated creatine kinase muscle damage'
    """
    try:
        results = _faiss_search("lab", query, top_k=3)
        output  = []
        for r in results:
            output.append({
                "test":                r.get("test", "N/A"),
                "abbreviation":        r.get("abbreviation", "N/A"),
                "panel":               r.get("panel", "N/A"),
                "normal_range":        r.get("normal_range_str", "N/A"),
                "high_interpretation": r.get("high_flag", "N/A"),
                "low_interpretation":  r.get("low_flag", "N/A"),
                "disease_context":     r.get("disease_context", "N/A"),
                "similarity":          round(r["_score"], 4),
            })
        return json.dumps(output, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": str(exc)})

# ---------------------------------------------------------------------------
# Tool 5 — get_hpo_terms
# ---------------------------------------------------------------------------

@tool
def get_hpo_terms(description: str) -> str:
    """
    Map a free-text clinical phenotype description to standardised Human
    Phenotype Ontology (HPO) terms. Use this to formalise phenotype descriptions,
    prepare data for Matchmaker Exchange, or structure a differential diagnosis.
    Returns HPO IDs and term names ranked by relevance.

    Args:
        description: Free-text clinical phenotype.
                     Example: 'proximal muscle weakness, elevated CK, cardiomyopathy in a child'
    """
    try:
        hpo_list = _get_hpo()
        try:
            results = _faiss_search("hpo", description, top_k=8)
            output  = [
                {
                    "hpo_id":     r.get("id", "N/A"),
                    "name":       r.get("name", "N/A"),
                    "definition": r.get("definition", "")[:200],
                    "similarity": round(r["_score"], 4),
                }
                for r in results
            ]
        except (FileNotFoundError, KeyError):
            output = _keyword_hpo_match(description, hpo_list, top_k=8)
        return json.dumps(output, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": str(exc)})

# ---------------------------------------------------------------------------
# HPO helpers
# ---------------------------------------------------------------------------

def _load_hpo_terms() -> list[dict]:
    """Load all HPO terms from hp.json (official OBO release)."""
    if not HPO_DATA_PATH.exists():
        return []
    with open(HPO_DATA_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    terms = []
    for node in raw.get("graphs", [{}])[0].get("nodes", []):
        node_id = node.get("id", "")
        if "HP_" not in node_id:
            continue
        hpo_id     = node_id.split("/")[-1].replace("_", ":")
        name       = node.get("lbl", "")
        definition = node.get("meta", {}).get("definition", {}).get("val", "")
        if name:
            terms.append({"id": hpo_id, "name": name, "definition": definition})
    return terms


def _keyword_hpo_match(description: str, hpo_list: list[dict], top_k: int) -> list[dict]:
    desc_tokens = set(description.lower().split())
    scored = []
    for term in hpo_list:
        overlap = len(desc_tokens & set(term.get("name", "").lower().split()))
        if overlap:
            scored.append((overlap, term))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "hpo_id":     t.get("id", "N/A"),
            "name":       t.get("name", "N/A"),
            "definition": t.get("definition", "")[:200],
            "similarity": round(score / max(len(desc_tokens), 1), 4),
        }
        for score, t in scored[:top_k]
    ]

# ---------------------------------------------------------------------------
# All tools as a list — imported by agents
# ---------------------------------------------------------------------------

ALL_TOOLS = [
    search_disease_profiles,
    search_case_reports,
    lookup_genetic_data,
    check_lab_values,
    get_hpo_terms,
]

# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        ("search_disease_profiles", {"query": "muscle weakness and respiratory failure"}),
        ("search_genetic_variants", {"query": "GAA gene pathogenic variant"}),
        ("check_lab_values",        {"query": "elevated creatine kinase"}),
        ("get_hpo_terms",           {"description": "proximal muscle weakness and cardiomyopathy"}),
    ]

    tool_map = {t.name: t for t in ALL_TOOLS}

    for tool_name, args in tests:
        print(f"\n{'='*60}")
        print(f"Tool  : {tool_name}")
        print(f"Args  : {args}")
        result = tool_map[tool_name].invoke(args)
        parsed = json.loads(result)
        if isinstance(parsed, list):
            print(f"Count : {len(parsed)} results")
            print(f"First : {json.dumps(parsed[0], indent=2)[:500]}")
        else:
            print(f"Error : {parsed}")