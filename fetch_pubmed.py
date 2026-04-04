import json
import time
import requests
import xml.etree.ElementTree as ET
import re

# ── CONFIG ────────────────────────────────────────────────────────────────────
PRODUCT1_PATH     = "datas/orpha_json/en_product1.json"
PRODUCT9_PATH     = "datas/orpha_json/en_product9_ages.json"  # has prevalence
OUTPUT_FILE       = "datas/rare_disease_abstracts.json"
MAX_DISEASES      = 500       # only fetch top N diseases
ABSTRACTS_PER_DISEASE = 3     # 3 good abstracts per disease
RATE_LIMIT        = 0.4       # seconds between requests
# ──────────────────────────────────────────────────────────────────────────────

BASE_SEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
BASE_FETCH  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def load_product1(path):
    """Load disease names and orphacodes from en_product1 NDJSON."""
    diseases = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "index" in record or "_index" in record:
                continue
            name  = record.get("Preferred term", "").strip()
            code  = str(record.get("ORPHAcode", "")).strip()
            # Only keep actual diseases, not groups or subtypes
            if name and code and record.get("Typology") == "Disease":
                diseases.append({"name": name, "orphacode": code})
    print(f"Loaded {len(diseases)} diseases from product1")
    return diseases


def load_prevalence_order(product9_path, diseases):
    """
    Try to order diseases by prevalence so we fetch
    the most common rare diseases first.
    Falls back to original order if product9 not available.
    """
    try:
        with open(product9_path, encoding="utf-8") as f:
            prev_data = {}
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except:
                    continue
                if "index" in record or "_index" in record:
                    continue
                code = str(record.get("ORPHAcode", ""))
                # Prevalence class as a rough ordering signal
                prev_list = record.get("AverageAgeOfOnset") or []
                if code and prev_list:
                    prev_data[code] = 1  # just mark as having data

        # Put diseases with known prevalence first
        with_prev    = [d for d in diseases if d["orphacode"] in prev_data]
        without_prev = [d for d in diseases if d["orphacode"] not in prev_data]
        ordered = with_prev + without_prev
        print(f"Ordered {len(with_prev)} diseases with prevalence data first")
        return ordered

    except FileNotFoundError:
        print("product9 not found — using original order")
        return diseases


def search_pubmed(disease_name, max_results=3):
    """Search PubMed for case reports about a disease. Returns list of PMIDs."""
    # Search specifically for case reports — most relevant for our diagnostic agent
    query = f'"{disease_name}"[Title/Abstract] AND ("case report"[pt] OR "case reports"[pt])'
    params = {
        "db":      "pubmed",
        "term":    query,
        "retmax":  max_results,
        "retmode": "json",
        "sort":    "relevance",
    }
    for attempt in range(3):
        try:
            r = requests.get(BASE_SEARCH, params=params, timeout=10)
            if r.status_code == 200:
                ids = r.json().get("esearchresult", {}).get("idlist", [])
                # If no case reports found, try without the filter
                if not ids:
                    params["term"] = f'"{disease_name}"[Title/Abstract]'
                    r2 = requests.get(BASE_SEARCH, params=params, timeout=10)
                    if r2.status_code == 200:
                        ids = r2.json().get("esearchresult", {}).get("idlist", [])
                return ids
        except Exception:
            pass
        time.sleep(2 ** attempt)
    return []


def fetch_abstracts_xml(pmids):
    """
    Fetch full records via XML — reliable abstract extraction.
    Returns list of abstract dicts.
    """
    if not pmids:
        return []

    params = {
        "db":      "pubmed",
        "id":      ",".join(pmids),
        "rettype": "abstract",
        "retmode": "xml",   # ← XML is reliable, JSON is not
    }

    for attempt in range(3):
        try:
            r = requests.get(BASE_FETCH, params=params, timeout=15)
            if r.status_code != 200:
                time.sleep(2 ** attempt)
                continue

            root     = ET.fromstring(r.text)
            articles = []

            for article_elem in root.findall(".//PubmedArticle"):

                pmid = article_elem.findtext(".//PMID", "").strip()

                # Title
                title_elem = article_elem.find(".//ArticleTitle")
                title = "".join(title_elem.itertext()).strip() if title_elem is not None else ""

                # Abstract — handles structured (Background/Methods/Results) format
                abstract_parts = article_elem.findall(".//AbstractText")
                if not abstract_parts:
                    continue  # no abstract — skip
                pieces = []
                for part in abstract_parts:
                    label = part.get("Label", "")
                    text  = "".join(part.itertext()).strip()
                    if text:
                        pieces.append(f"{label}: {text}" if label else text)
                abstract = " ".join(pieces).strip()
                if not abstract:
                    continue

                # Publication year
                pub_year = (
                    article_elem.findtext(".//PubDate/Year")
                    or article_elem.findtext(".//PubDate/MedlineDate", "")[:4]
                    or ""
                ).strip()

                # Authors
                authors = []
                for author in article_elem.findall(".//Author"):
                    last     = author.findtext("LastName", "").strip()
                    initials = author.findtext("Initials", "").strip()
                    if last:
                        authors.append(f"{last} {initials}".strip())

                # Journal
                journal = (
                    article_elem.findtext(".//Journal/Title")
                    or article_elem.findtext(".//MedlineTA")
                    or ""
                ).strip()

                # MeSH terms
                mesh_terms = [
                    mesh.findtext("DescriptorName", "").strip()
                    for mesh in article_elem.findall(".//MeshHeading")
                    if mesh.findtext("DescriptorName", "").strip()
                ]

                # Publication types
                pub_types = [
                    pt.text.strip()
                    for pt in article_elem.findall(".//PublicationType")
                    if pt.text
                ]

                articles.append({
                    "pmid":              pmid,
                    "title":             title,
                    "abstract":          abstract,
                    "pub_year":          pub_year,
                    "authors":           authors,
                    "journal":           journal,
                    "mesh_terms":        mesh_terms,
                    "publication_types": pub_types,
                })

            return articles

        except ET.ParseError as e:
            print(f"    XML parse error attempt {attempt+1}: {e}")
        except Exception as e:
            print(f"    Error attempt {attempt+1}: {e}")
        time.sleep(2 ** attempt)

    return []


# ── MAIN ──────────────────────────────────────────────────────────────────────
import os
os.makedirs("data/raw/pubmed", exist_ok=True)

# Load and order diseases
all_diseases = load_product1(PRODUCT1_PATH)
all_diseases = load_prevalence_order(PRODUCT9_PATH, all_diseases)
diseases     = all_diseases[:MAX_DISEASES]  # top 500 only
print(f"Will fetch abstracts for {len(diseases)} diseases")

# Resume support — don't re-fetch what we already have
try:
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        results = json.load(f)
    already = {r["orphacode"] for r in results}
    print(f"Resuming — {len(results)} already done, skipping them")
except (FileNotFoundError, json.JSONDecodeError):
    results  = []
    already  = set()

# Fetch
for i, disease in enumerate(diseases):
    if disease["orphacode"] in already:
        continue

    pmids     = search_pubmed(disease["name"], ABSTRACTS_PER_DISEASE)
    time.sleep(RATE_LIMIT)
    abstracts = fetch_abstracts_xml(pmids)
    time.sleep(RATE_LIMIT)

    results.append({
        "orphacode": disease["orphacode"],
        "disease":   disease["name"],
        "abstracts": abstracts,         # list of full abstract dicts
    })
    already.add(disease["orphacode"])

    # Save every 50 diseases so we don't lose progress
    if (i + 1) % 50 == 0:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        fetched = sum(1 for r in results if r["abstracts"])
        total_abstracts = sum(len(r["abstracts"]) for r in results)
        print(f"Progress: {i+1}/{len(diseases)} diseases | "
              f"{fetched} with abstracts | "
              f"{total_abstracts} total abstracts")

# Final save
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

# Final report
fetched         = sum(1 for r in results if r["abstracts"])
total_abstracts = sum(len(r["abstracts"]) for r in results)
print(f"\nDone!")
print(f"Diseases processed : {len(results)}")
print(f"With abstracts     : {fetched}")
print(f"Total abstracts    : {total_abstracts}")
print(f"Saved to           : {OUTPUT_FILE}")