# Rare Disease RAG System — Data Collection Guide

This document explains how to download and prepare all data sources used by the multi-agent RAG system for rare disease diagnosis.

---

## Overview

The system uses 5 data sources, all free and publicly accessible:

| Source | What it provides | Format |
|---|---|---|
| Orphanet (Orphadata) | Disease profiles, symptoms, genes, epidemiology | XML → JSON |
| HPO | Symptom ontology tree + hierarchy | OBO |
| ClinVar | Pathogenic genetic variants linked to diseases | TSV.GZ → JSON |
| PubMed | Research abstracts per disease | fetched via API |
| LabQAR | Lab test reference ranges (LOINC-mapped) | CSV/JSON |

---

## Prerequisites

Install required Python libraries:
```bash
pip install requests
```

---

## Source 1: Orphanet (Orphadata)

### Step 1 — Clone the Orphanet API repo

```bash
git clone https://github.com/Orphanet/API_Orphadata.git
cd API_Orphadata
pip install -r requirements.txt
```

### Step 2 — Download all XML files

```bash
python datas/orphadata_download.py
```

Files are saved to `datas/xml_data/`.

### Step 3 — Delete files you don't need

Keep only these 5 English files and delete everything else:

```
en_product1.xml       ← disease names + ICD-10/OMIM/UMLS cross-references
en_product4.xml       ← disease ↔ HPO symptom annotations with frequency
en_product6.xml       ← disease ↔ causative genes
en_product9_ages.xml  ← age of onset + inheritance pattern
en_product9_prev.xml  ← disease prevalence
```

Delete all `fr_`, `de_`, `pt_` and other non-English files. Delete all `en_product3_*.xml` and `en_product7.xml` files — these are classification/admin files not needed for diagnosis.

```powershell
# Delete all non-English files
Get-ChildItem -Filter "*.xml" | Where-Object { $_.Name -notmatch "^en_" } | Remove-Item

# Delete product3 and product7
Get-ChildItem -Filter "en_product3_*.xml" | Remove-Item
Remove-Item en_product7.xml -ErrorAction SilentlyContinue
```

### Step 4 — Convert XML to JSON

```bash
python datas/src/orphadata_xml2json.py
```

JSON files are saved to `datas/json_data/`.

**Final output:** 5 JSON files

---

## Source 2: HPO — Human Phenotype Ontology

Download the ontology file using its permanent URL:

```powershell
Invoke-WebRequest -Uri "http://purl.obolibrary.org/obo/hp.obo" -OutFile "hp.obo"
```
> **Note:** `phenotype.hpoa` (disease-symptom annotations) is not separately needed — this information is already covered by Orphanet `en_product4.xml`.

**Final output:** `hp.obo`

---

## Source 3: ClinVar

### Step 1 — Download

```powershell
Invoke-WebRequest -Uri "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz" -OutFile "variant_summary.txt.gz"
```

File size: ~435MB compressed.

### Step 2 — Filter

Run `filter_clinvar.py` in the same folder as the downloaded file.

```bash
python filter_clinvar.py
```


**Final output:** `clinvar_filtered.json`, ~50–80MB.

---

## Source 4: PubMed Abstracts

This is a batch fetch — the script queries PubMed for each disease name from your Orphanet data and saves the top 5 abstracts per disease.

> **Optional but recommended:** Get a free NCBI API key at https://ncbi.nlm.nih.gov/account/ — raises rate limit from 3 to 10 requests/second and speeds up the fetch significantly.

Run `fetch_pubmed.py` and run it from the folder containing your Orphanet JSON files:

```bash
python fetch_pubmed.py
```

**Final output:** `rare_disease_abstracts.json`, ~150–250MB.

---

## Source 5: LabQAR — Lab Reference Ranges

Generate a sample json with around 200 reports.

**Final output:** CSV/JSON files

---
