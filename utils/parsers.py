import json
import re
from collections import defaultdict

# HELPER FUNCTIONS

def load_ndjson(path: str) -> list:
    """
    Reads an Orphanet NDJSON file.
    Skips index lines like {"index": {"_index": "..."}}
    Returns list of data records.
    """
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            # Skip Elasticsearch index lines
            if "index" in obj or "_index" in obj:
                continue
            records.append(obj)
    return records


def strip_html(text: str) -> str:
    """Remove HTML tags like <i>, <b> from Orphanet definition text."""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


#PARSER 1: en_product1

def parse_product1(path: str) -> dict:
    """
    Parses en_product1.json — disease names, definitions, synonyms, external refs.
    Returns dict keyed by orphacode string.

    Key fields extracted:
      - name          : "Preferred term"
      - synonyms      : "Synonym" list (can be null)
      - definition    : "SummaryInformation[0].Definition" (HTML stripped)
      - external_refs : {Source: Reference} for OMIM, ICD-10, ICD-11, MONDO
      - typology      : "Disease" / "Clinical group" / etc
    """
    records = load_ndjson(path)
    diseases = {}

    for rec in records:
        code = str(rec.get("ORPHAcode", "")).strip()
        if not code:
            continue

        # Synonyms — can be null or a list
        raw_syn = rec.get("Synonym") or []
        if isinstance(raw_syn, str):
            raw_syn = [raw_syn]
        synonyms = [s.strip() for s in raw_syn if s and s.strip()]

        # Definition — strip HTML tags
        definition = ""
        summary = rec.get("SummaryInformation") or []
        if summary and isinstance(summary, list):
            raw_def = summary[0].get("Definition", "") or ""
            definition = strip_html(raw_def)

        # External refs — keep only the sources we care about
        KEEP = {"OMIM", "ICD-10", "ICD-11", "MONDO", "MeSH"}
        ext_refs = {}
        for ref in (rec.get("ExternalReference") or []):
            src = ref.get("Source", "")
            if src in KEEP:
                ext_refs[src] = ref.get("Reference", "")

        diseases[code] = {
            "orphacode":      code,
            "name":           rec.get("Preferred term", "").strip(),
            "synonyms":       synonyms,
            "definition":     definition,
            "typology":       rec.get("Typology", ""),
            "disorder_group": rec.get("DisorderGroup", ""),
            "external_refs":  ext_refs,
            # placeholders — filled by later parsers
            "symptoms":       [],
            "genes":          [],
            "onset":          [],
            "inheritance":    [],
            "abstracts":      [],
        }

    print(f"[product1] {len(diseases)} records loaded")
    return diseases


#PARSER 2: en_product4 

def parse_product4(path: str) -> dict:
    """
    Parses en_product4.json — HPO symptom associations per disease.
    Returns dict keyed by orphacode string.

    Structure: each record has "Disorder" → "HPODisorderAssociation" list
    Each association has "HPO" → {"HPOId", "HPOTerm"} + "HPOFrequency"

    Returns: {orphacode: [{"hpo_id": ..., "term": ..., "frequency": ...}]}
    """
    records = load_ndjson(path)
    symptom_map = {}

    for rec in records:
        disorder = rec.get("Disorder", {})
        code = str(disorder.get("ORPHAcode", "")).strip()
        if not code:
            continue

        associations = disorder.get("HPODisorderAssociation") or []
        symptoms = []

        for assoc in associations:
            hpo = assoc.get("HPO", {})
            hpo_id   = hpo.get("HPOId", "")
            hpo_term = hpo.get("HPOTerm", "").strip()
            frequency = assoc.get("HPOFrequency", "").strip()

            if hpo_term:
                symptoms.append({
                    "hpo_id":    hpo_id,
                    "term":      hpo_term,
                    "frequency": frequency,
                })

        symptom_map[code] = symptoms

    print(f"[product4] {len(symptom_map)} diseases with HPO symptoms")
    return symptom_map


#PARSER 3: en_product6

def parse_product6(path: str) -> dict:
    """
    Parses en_product6.json — gene associations per disease.
    Returns dict keyed by orphacode string.

    Structure: "DisorderGeneAssociation" list → each has "Gene" → "Symbol"

    Returns: {orphacode: [{"symbol": ..., "name": ..., "type": ...}]}
    """
    records = load_ndjson(path)
    gene_map = {}

    for rec in records:
        code = str(rec.get("ORPHAcode", "")).strip()
        if not code:
            continue

        associations = rec.get("DisorderGeneAssociation") or []
        genes = []

        for assoc in associations:
            gene = assoc.get("Gene", {})
            symbol = gene.get("Symbol", "").strip()
            name   = gene.get("Preferred term", "").strip()
            gtype  = gene.get("GeneType", "").strip()

            if symbol:
                genes.append({
                    "symbol": symbol,
                    "name":   name,
                    "type":   gtype,
                })

        gene_map[code] = genes

    print(f"[product6] {len(gene_map)} diseases with gene associations")
    return gene_map


#PARSER 4: en_product9

def parse_product9(path: str) -> dict:
    """
    Parses en_product9_ages.json — onset age and inheritance pattern.
    Returns dict keyed by orphacode string.

    Fields: "AverageAgeOfOnset" (list of strings), "TypeOfInheritance" (list)

    Returns: {orphacode: {"onset": [...], "inheritance": [...]}}
    """
    records = load_ndjson(path)
    onset_map = {}

    for rec in records:
        code = str(rec.get("ORPHAcode", "")).strip()
        if not code:
            continue

        onset = [
            o.strip() for o in (rec.get("AverageAgeOfOnset") or [])
            if o and o.strip()
        ]
        inheritance = [
            i.strip() for i in (rec.get("TypeOfInheritance") or [])
            if i and i.strip()
        ]

        onset_map[code] = {
            "onset":       onset,
            "inheritance": inheritance,
        }

    print(f"[product9] {len(onset_map)} diseases with onset/inheritance data")
    return onset_map


#PARSER 5: hp.json

def parse_hp(path: str) -> dict:
    """
    Parses hp.json — the HPO ontology.
    Builds a lookup: HP:xxxxxxx → {"label": ..., "definition": ..., "synonyms": [...]}

    Structure: data["graphs"][0]["nodes"] — each node is one HPO term.
    Node id format: "http://purl.obolibrary.org/obo/HP_0000001"
    We convert to standard "HP:0000001" format.
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    nodes = data["graphs"][0].get("nodes", [])
    hp_map = {}

    for node in nodes:
        raw_id = node.get("id", "")
        # Convert URL format to HP:xxxxxxx format
        # "http://.../HP_0000256" → "HP:0000256"
        if "HP_" not in raw_id:
            continue
        hp_id = "HP:" + raw_id.split("HP_")[-1]

        # Label (term name)
        label = node.get("lbl", "").strip()
        if not label:
            continue

        # Definition
        definition = ""
        meta = node.get("meta", {})
        def_list = meta.get("definition", {})
        if isinstance(def_list, dict):
            definition = strip_html(def_list.get("val", ""))
        elif isinstance(def_list, list) and def_list:
            definition = strip_html(def_list[0].get("val", ""))

        # Synonyms
        synonyms = []
        for syn in meta.get("synonyms", []):
            val = syn.get("val", "").strip()
            if val:
                synonyms.append(val)

        hp_map[hp_id] = {
            "label":      label,
            "definition": definition,
            "synonyms":   synonyms,
        }

    print(f"[hp.json] {len(hp_map)} HPO terms loaded")
    return hp_map


#PARSER 6: clinvar_filtered.json

def parse_clinvar(path: str) -> dict:
    """
    Parses clinvar_filtered.json — pathogenic genetic variants.
    Already a clean JSON array from our earlier filter script.

    Fields available: variant_id, name, gene, significance,
                      review_status, condition, condition_db_ids,
                      variant_type, chromosome, assembly, omim_ids

    Returns two structures:
      gene_to_variants : {gene_symbol: [list of variant dicts]}
      omim_to_variants : {omim_id: [list of variant dicts]}
    """
    with open(path, encoding="utf-8") as f:
        records = json.load(f)

    gene_to_variants = defaultdict(list)
    omim_to_variants = defaultdict(list)

    for rec in records:
        gene = rec.get("gene", "").strip()
        if not gene:
            continue

        variant = {
            "variant_id":   rec.get("variant_id", ""),
            "name":         rec.get("name", ""),
            "gene":         gene,
            "significance": rec.get("significance", ""),
            "condition":    rec.get("condition", ""),
            "variant_type": rec.get("variant_type", ""),
            "review_status":rec.get("review_status", ""),
        }

        gene_to_variants[gene].append(variant)

        # Also index by OMIM ID if present
        omim_ids = rec.get("omim_ids", "") or ""
        for part in omim_ids.split(","):
            part = part.strip()
            if part.startswith("OMIM:"):
                omim_id = part.replace("OMIM:", "").strip()
                if omim_id:
                    omim_to_variants[omim_id].append(variant)

    print(f"[clinvar] {len(gene_to_variants)} unique genes")
    print(f"[clinvar] {len(omim_to_variants)} OMIM IDs indexed")
    print(f"[clinvar] {sum(len(v) for v in gene_to_variants.values())} total variants")

    return dict(gene_to_variants), dict(omim_to_variants)


#PARSER 7: PubMed abstracts

def parse_pubmed(path: str) -> dict:
    """
    Parses rare_disease_abstracts.json.
    Returns dict keyed by orphacode string.

    Each value is a list of abstract dicts with:
      pmid, title, abstract, pub_year, authors, journal,
      mesh_terms, publication_types
    """
    with open(path, encoding="utf-8") as f:
        records = json.load(f)

    pubmed_map = {}
    for rec in records:
        code = str(rec.get("orphacode", "")).strip()
        if not code:
            continue
        pubmed_map[code] = rec.get("abstracts", [])

    total_abstracts = sum(len(v) for v in pubmed_map.values())
    print(f"[pubmed] {len(pubmed_map)} diseases with abstract entries")
    print(f"[pubmed] {total_abstracts} total abstracts")
    return pubmed_map


#MERGER: build unified disease records
def build_unified_records(
    product1_path: str,
    product4_path: str,
    product6_path: str,
    product9_path: str,
    hp_path:       str,
    pubmed_path:   str,
) -> dict:
    """
    Merges all parsers into one unified dict of disease records.
    Keyed by orphacode string.
    Each record has all fields + a rag_text field ready for embedding.
    """
    print("\n── Loading all data sources ──────────────────────────")
    diseases      = parse_product1(product1_path)
    symptom_map   = parse_product4(product4_path)
    gene_map      = parse_product6(product6_path)
    onset_map     = parse_product9(product9_path)
    hp_lookup     = parse_hp(hp_path)
    pubmed_map    = parse_pubmed(pubmed_path)

    print("\n── Merging into unified records ──────────────────────")

    for code, disease in diseases.items():

        # Attach symptoms from product4
        raw_symptoms = symptom_map.get(code, [])
        # Use readable HPO terms directly — they're already in product4
        disease["symptoms"] = [s["term"] for s in raw_symptoms]
        # Keep full symptom data including frequency
        disease["symptoms_full"] = raw_symptoms

        # Attach genes from product6
        raw_genes = gene_map.get(code, [])
        disease["genes"] = [g["symbol"] for g in raw_genes]
        disease["genes_full"] = raw_genes

        # Attach onset + inheritance from product9
        onset_data = onset_map.get(code, {})
        disease["onset"]       = onset_data.get("onset", [])
        disease["inheritance"] = onset_data.get("inheritance", [])

        # Attach PubMed abstracts
        disease["abstracts"] = pubmed_map.get(code, [])

        # Build RAG text — this is what gets embedded into FAISS
        disease["rag_text"] = build_rag_text(disease)

    print(f"\n── Merge complete ────────────────────────────────────")
    print(f"Total diseases         : {len(diseases)}")
    print(f"With symptoms          : {sum(1 for d in diseases.values() if d['symptoms'])}")
    print(f"With genes             : {sum(1 for d in diseases.values() if d['genes'])}")
    print(f"With onset data        : {sum(1 for d in diseases.values() if d['onset'])}")
    print(f"With definition        : {sum(1 for d in diseases.values() if d['definition'])}")
    print(f"With PubMed abstracts  : {sum(1 for d in diseases.values() if d['abstracts'])}")

    return diseases


def build_rag_text(disease: dict) -> str:
    """
    Builds the rich text string that gets embedded into FAISS.
    The richer and more specific this text, the better the semantic search.
    Order matters — most important info first.
    """
    parts = []

    # Core identity
    parts.append(f"Disease: {disease['name']}")
    parts.append(f"OrphaCode: {disease['orphacode']}")

    if disease.get("synonyms"):
        parts.append(f"Also known as: {', '.join(disease['synonyms'])}")

    # Clinical description
    if disease.get("definition"):
        parts.append(f"Description: {disease['definition']}")

    # Symptoms — most important for diagnostic matching
    if disease.get("symptoms"):
        parts.append(f"Clinical features: {', '.join(disease['symptoms'])}")

    # Genetics
    if disease.get("genes"):
        parts.append(f"Associated genes: {', '.join(disease['genes'])}")

    # Onset and inheritance
    if disease.get("onset"):
        parts.append(f"Age of onset: {', '.join(disease['onset'])}")

    if disease.get("inheritance"):
        parts.append(f"Inheritance: {', '.join(disease['inheritance'])}")

    # Cross-references
    if disease.get("external_refs"):
        refs = ", ".join(
            f"{src}:{code}"
            for src, code in disease["external_refs"].items()
        )
        parts.append(f"Cross-references: {refs}")

    # Case reports — only include abstract text, not metadata
    abstracts = disease.get("abstracts", [])
    for i, ab in enumerate(abstracts[:2]):  # max 2 abstracts in RAG text
        abstract_text = ab.get("abstract", "").strip()
        if abstract_text:
            year  = ab.get("pub_year", "")
            year_str = f" ({year})" if year else ""
            parts.append(f"Case report{year_str}: {abstract_text[:400]}")

    return "\n".join(parts)


#TEST
if __name__ == "__main__":
    PATHS = {
        "product1": "../datas/orpha_json/en_product1.json",
        "product4": "../datas/orpha_json/en_product4.json",
        "product6": "../datas/orpha_json/en_product6.json",
        "product9": "../datas/orpha_json/en_product9_ages.json",
        "hp":       "../datas/hp.json",
        "pubmed":   "../datas/rare_disease_abstracts.json",
    }

    diseases = build_unified_records(
        PATHS["product1"],
        PATHS["product4"],
        PATHS["product6"],
        PATHS["product9"],
        PATHS["hp"],
        PATHS["pubmed"],
    )

    # Show 2 sample records — one with abstracts, one without
    print("\n── Sample records ──")

    # Find one with abstracts
    with_abs = next(
        (d for d in diseases.values() if d["abstracts"]), None
    )
    # Find one without
    without_abs = next(
        (d for d in diseases.values() if not d["abstracts"] and d["definition"]), None
    )

    for label, sample in [("WITH abstracts", with_abs), ("WITHOUT abstracts", without_abs)]:
        if not sample:
            continue
        print(f"\n{'='*55}")
        print(f"SAMPLE ({label}): {sample['name']}")
        print(f"Symptoms  : {sample['symptoms'][:5]}")
        print(f"Genes     : {sample['genes']}")
        print(f"Onset     : {sample['onset']}")
        print(f"Abstracts : {len(sample['abstracts'])}")
        print(f"\nRAG TEXT:\n{sample['rag_text'][:800]}")
        print("...")