import json
import re
from collections import defaultdict


# ── HELPER FUNCTIONS ──────────────────────────────────────────────────────────

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
            if "index" in obj or "_index" in obj:
                continue
            records.append(obj)
    return records


def strip_html(text: str) -> str:
    """Remove HTML tags like <i>, <b> from Orphanet definition text."""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


# ── PARSER 1: en_product1 ─────────────────────────────────────────────────────

def parse_product1(path: str) -> dict:
    """
    Parses en_product1.json — disease names, definitions, synonyms, external refs.
    Returns dict keyed by orphacode string.
    Filters out OBSOLETE and NON RARE IN EUROPE entries.
    """
    records = load_ndjson(path)
    diseases = {}

    for rec in records:
        code = str(rec.get("ORPHAcode", "")).strip()
        if not code:
            continue

        name = rec.get("Preferred term", "").strip()

        # ── FIX 1: Filter obsolete and non-rare entries ──
        if not name:
            continue
        if name.startswith("OBSOLETE:") or name.startswith("NON RARE IN EUROPE:"):
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
            "name":           name,
            "synonyms":       synonyms,
            "definition":     definition,
            "typology":       rec.get("Typology", ""),
            "disorder_group": rec.get("DisorderGroup", ""),
            "external_refs":  ext_refs,
            # placeholders — filled by later parsers
            "symptoms":       [],
            "symptoms_full":  [],
            "genes":          [],
            "genes_full":     [],
            "onset":          [],
            "inheritance":    [],
            "abstracts":      [],
        }

    print(f"[product1] {len(diseases)} records loaded (OBSOLETE/NON RARE filtered)")
    return diseases


# ── PARSER 2: en_product4 ─────────────────────────────────────────────────────

def parse_product4(path: str) -> dict:
    """
    Parses en_product4.json — HPO symptom associations per disease.
    Returns dict keyed by orphacode string.

    Each association has HPOId, HPOTerm, and HPOFrequency.
    """
    records = load_ndjson(path)
    symptom_map = {}

    for rec in records:
        # ── FIX 2: Fallback for orphacode location ──
        disorder = rec.get("Disorder", {})
        code = str(
            disorder.get("ORPHAcode", "") or rec.get("ORPHAcode", "")
        ).strip()
        if not code:
            continue

        associations = disorder.get("HPODisorderAssociation") or []
        if not associations:
            # fallback: maybe associations are at top level
            associations = rec.get("HPODisorderAssociation") or []

        symptoms = []
        for assoc in associations:
            hpo      = assoc.get("HPO", {})
            hpo_id   = hpo.get("HPOId", "").strip()
            hpo_term = hpo.get("HPOTerm", "").strip()

            # Frequency can be a string or nested dict
            freq_raw = assoc.get("HPOFrequency", "")
            if isinstance(freq_raw, dict):
                frequency = freq_raw.get("Name", "") or freq_raw.get("Label", "")
            else:
                frequency = str(freq_raw).strip()

            if hpo_term:
                symptoms.append({
                    "hpo_id":    hpo_id,
                    "term":      hpo_term,
                    "frequency": frequency,
                })

        symptom_map[code] = symptoms

    print(f"[product4] {len(symptom_map)} diseases with HPO symptoms")
    return symptom_map


# ── PARSER 3: en_product6 ─────────────────────────────────────────────────────

def parse_product6(path: str) -> dict:
    """
    Parses en_product6.json — gene associations per disease.
    Returns dict keyed by orphacode string.
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
            gene   = assoc.get("Gene", {})
            symbol = gene.get("Symbol", "").strip()
            name   = gene.get("Preferred term", "").strip()

            # ── FIX 3: GeneType is a nested list/dict ──
            gtype_raw = gene.get("GeneType") or []
            if isinstance(gtype_raw, list):
                gtype = gtype_raw[0].get("Name", "") if gtype_raw and isinstance(gtype_raw[0], dict) else (gtype_raw[0] if gtype_raw else "")
            elif isinstance(gtype_raw, dict):
                gtype = gtype_raw.get("Name", "")
            else:
                gtype = str(gtype_raw).strip()

            if symbol:
                genes.append({
                    "symbol": symbol,
                    "name":   name,
                    "type":   gtype,
                })

        gene_map[code] = genes

    print(f"[product6] {len(gene_map)} diseases with gene associations")
    return gene_map


# ── PARSER 4: en_product9 ─────────────────────────────────────────────────────

def parse_product9(path: str) -> dict:
    """
    Parses en_product9_ages.json — onset age and inheritance pattern.
    Returns dict keyed by orphacode string.

    AverageAgeOfOnset and TypeOfInheritance can be lists of strings
    or lists of dicts with a "Name" key depending on Orphanet version.
    """
    records = load_ndjson(path)
    onset_map = {}

    for rec in records:
        code = str(rec.get("ORPHAcode", "")).strip()
        if not code:
            continue

        def extract_list(field):
            raw = rec.get(field) or []
            result = []
            for item in raw:
                if isinstance(item, dict):
                    # Try all possible key names
                    val = (item.get("Name") or 
                        item.get("Label") or 
                        item.get("Preferred term") or 
                        item.get("value") or "")
                else:
                    val = str(item)
                val = val.strip()
                if val:
                    result.append(val)
            return result

        onset_map[code] = {
            "onset":       extract_list("AverageAgeOfOnset"),
            "inheritance": extract_list("TypeOfInheritance"),
        }

    print(f"[product9] {len(onset_map)} diseases with onset/inheritance data")
    return onset_map


# ── PARSER 5: hp.json ─────────────────────────────────────────────────────────

def parse_hp(path: str) -> dict:
    """
    Parses hp.json — the HPO ontology.
    Builds lookup: HP:xxxxxxx → {label, definition, synonyms}
    Used to enrich symptom text in RAG embeddings.
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    nodes = data["graphs"][0].get("nodes", [])
    hp_map = {}

    for node in nodes:
        raw_id = node.get("id", "")
        if "HP_" not in raw_id:
            continue
        hp_id = "HP:" + raw_id.split("HP_")[-1]

        label = node.get("lbl", "").strip()
        if not label:
            continue

        definition = ""
        meta = node.get("meta", {})
        def_raw = meta.get("definition", {})
        if isinstance(def_raw, dict):
            definition = strip_html(def_raw.get("val", ""))
        elif isinstance(def_raw, list) and def_raw:
            definition = strip_html(def_raw[0].get("val", ""))

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


# ── PARSER 6: clinvar_filtered.json ──────────────────────────────────────────

def parse_clinvar(path: str) -> tuple:
    """
    Parses clinvar_filtered.json — pathogenic genetic variants.
    Returns:
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
            "variant_id":    rec.get("variant_id", ""),
            "name":          rec.get("name", ""),
            "gene":          gene,
            "significance":  rec.get("significance", ""),
            "condition":     rec.get("condition", ""),
            "variant_type":  rec.get("variant_type", ""),
            "review_status": rec.get("review_status", ""),
        }

        gene_to_variants[gene].append(variant)

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


# ── PARSER 7: PubMed abstracts ────────────────────────────────────────────────

def parse_pubmed(path: str) -> dict:
    """
    Parses rare_disease_abstracts.json.
    Returns dict keyed by orphacode string.
    Each value is a list of abstract dicts.
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


# ── MERGER: build unified disease records ─────────────────────────────────────

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
    diseases    = parse_product1(product1_path)
    symptom_map = parse_product4(product4_path)
    gene_map    = parse_product6(product6_path)
    onset_map   = parse_product9(product9_path)
    hp_lookup   = parse_hp(hp_path)
    pubmed_map  = parse_pubmed(pubmed_path)

    print("\n── Merging into unified records ──────────────────────")

    for code, disease in diseases.items():

        # Symptoms from product4
        raw_symptoms = symptom_map.get(code, [])
        disease["symptoms_full"] = raw_symptoms
        disease["symptoms"]      = [s["term"] for s in raw_symptoms]

        # Genes from product6
        raw_genes = gene_map.get(code, [])
        disease["genes_full"] = raw_genes
        disease["genes"]      = [g["symbol"] for g in raw_genes]

        # Onset + inheritance from product9
        onset_data             = onset_map.get(code, {})
        disease["onset"]       = onset_data.get("onset", [])
        disease["inheritance"] = onset_data.get("inheritance", [])

        # PubMed abstracts
        disease["abstracts"] = pubmed_map.get(code, [])

        # Build RAG text using hp_lookup for enrichment
        disease["rag_text"] = build_rag_text(disease, hp_lookup)

    print(f"\n── Merge complete ────────────────────────────────────")
    print(f"Total diseases         : {len(diseases)}")
    print(f"With symptoms          : {sum(1 for d in diseases.values() if d['symptoms'])}")
    print(f"With genes             : {sum(1 for d in diseases.values() if d['genes'])}")
    print(f"With onset data        : {sum(1 for d in diseases.values() if d['onset'])}")
    print(f"With definition        : {sum(1 for d in diseases.values() if d['definition'])}")
    print(f"With PubMed abstracts  : {sum(1 for d in diseases.values() if d['abstracts'])}")

    return diseases


# ── RAG TEXT BUILDER ──────────────────────────────────────────────────────────

def build_rag_text(disease: dict, hp_lookup: dict = None) -> str:
    """
    Builds the rich text string that gets embedded into FAISS.
    Includes frequency-tiered symptoms for better diagnostic matching.
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

    # ── FIX 4: Frequency-tiered symptoms ──
    symptoms_full = disease.get("symptoms_full", [])
    if symptoms_full:
        obligate   = []
        frequent   = []
        occasional = []

        for s in symptoms_full:
            term = s["term"]
            freq = s.get("frequency", "").lower()

            # Enrich term with HPO definition if available
            if hp_lookup and s.get("hpo_id"):
                hp_entry = hp_lookup.get(s["hpo_id"], {})
                hp_def   = hp_entry.get("definition", "")
                # Only append definition if it adds useful info
                if hp_def and hp_def.lower() != term.lower():
                    term = f"{term}"  # keep clean, definition adds noise

            if "obligate" in freq or "100%" in freq:
                obligate.append(term)
            elif "very frequent" in freq or "frequent" in freq:
                frequent.append(term)
            elif "occasional" in freq or "rare" in freq or "excluded" in freq:
                occasional.append(term)
            else:
                frequent.append(term)  # default to frequent if unknown

        if obligate:
            parts.append(
                f"Obligate features (always present): {', '.join(obligate)}"
            )
        if frequent:
            parts.append(
                f"Frequent features: {', '.join(frequent[:15])}"
            )
        if occasional:
            parts.append(
                f"Occasional features: {', '.join(occasional[:8])}"
            )

    elif disease.get("symptoms"):
        # Fallback if symptoms_full is empty but symptoms list exists
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
            f"{src}:{ref}"
            for src, ref in disease["external_refs"].items()
        )
        parts.append(f"Cross-references: {refs}")

    # Case reports — max 2, truncated to 400 chars
    for ab in disease.get("abstracts", [])[:2]:
        abstract_text = ab.get("abstract", "").strip()
        if abstract_text:
            year     = ab.get("pub_year", "")
            year_str = f" ({year})" if year else ""
            parts.append(
                f"Case report{year_str}: {abstract_text[:400]}"
            )

    return "\n".join(parts)


# ── TEST ─

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

    # Show sample records
    print("\n── Sample records ──")

    with_abs    = next((d for d in diseases.values() if d["abstracts"]), None)
    without_abs = next((d for d in diseases.values()
                        if not d["abstracts"] and d["definition"]), None)

    for label, sample in [("WITH abstracts", with_abs),
                           ("WITHOUT abstracts", without_abs)]:
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