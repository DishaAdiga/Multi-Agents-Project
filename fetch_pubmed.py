import json
import time
import requests
import os

ORPHANET_PRODUCT1 = "en_product1.json"   # update path if needed
OUTPUT_FILE = "pubmed_abstracts.json"
NCBI_API_KEY = ""   # paste your key here, or leave empty

BASE_SEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
BASE_FETCH  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

RATE_LIMIT  = 0.11 if NCBI_API_KEY else 0.34   # seconds between requests

def search_pubmed(disease_name):
    params = {
        "db": "pubmed",
        "term": f'"{disease_name}"[Title/Abstract] rare disease',
        "retmax": 5,
        "retmode": "json",
    }
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    r = requests.get(BASE_SEARCH, params=params, timeout=10)
    r.raise_for_status()
    return r.json().get("esearchresult", {}).get("idlist", [])

def fetch_abstracts(pmids):
    if not pmids:
        return []
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "json",
    }
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    r = requests.get(BASE_FETCH, params=params, timeout=15)
    r.raise_for_status()
    articles = []
    data = r.json().get("result", {})
    for pmid in pmids:
        article = data.get(pmid, {})
        title = article.get("title", "")
        abstract_list = article.get("abstract", {}).get("abstracttext", [])
        abstract = " ".join(
            a.get("value", a) if isinstance(a, dict) else a
            for a in abstract_list
        ) if isinstance(abstract_list, list) else str(abstract_list)
        if title or abstract:
            articles.append({"pmid": pmid, "title": title, "abstract": abstract})
    return articles

# Load disease names from Orphanet product1
with open(ORPHANET_PRODUCT1, encoding="utf-8") as f:
    product1 = json.load(f)

# Extract disease names — adjust key path if your JSON structure differs
diseases = []
for entry in product1.get("JDBOR", [{}])[0].get("DisorderList", {}).get("Disorder", []):
    name = entry.get("Name", {}).get("#text", "")
    orpha = entry.get("OrphaCode", "")
    if name:
        diseases.append({"name": name, "orphacode": orpha})

print(f"Found {len(diseases)} diseases. Starting fetch...")

results = []
for i, disease in enumerate(diseases):
    try:
        pmids = search_pubmed(disease["name"])
        time.sleep(RATE_LIMIT)
        abstracts = fetch_abstracts(pmids)
        time.sleep(RATE_LIMIT)
        if abstracts:
            results.append({
                "orphacode": disease["orphacode"],
                "disease": disease["name"],
                "abstracts": abstracts
            })
    except Exception as e:
        print(f"  Error on {disease['name']}: {e}")
        time.sleep(2)

    if (i + 1) % 100 == 0:
        print(f"  Progress: {i+1}/{len(diseases)} diseases fetched")
        # Save checkpoint every 100 diseases
        with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
            json.dump(results, out, indent=2)

# Final save
with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
    json.dump(results, out, indent=2)

print(f"\nDone. Saved abstracts for {len(results)} diseases to {OUTPUT_FILE}")