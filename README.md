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
python datas/src/orphadata_download.py
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

**PowerShell:**
```powershell
# Delete all non-English files
Get-ChildItem -Filter "*.xml" | Where-Object { $_.Name -notmatch "^en_" } | Remove-Item

# Delete product3 and product7
Get-ChildItem -Filter "en_product3_*.xml" | Remove-Item
Remove-Item en_product7.xml -ErrorAction SilentlyContinue
```

**bash:**
```bash
# Delete all non-English files
find . -name "*.xml" ! -name "en_*" -delete

# Delete product3 and product7
rm -f en_product3_*.xml en_product7.xml
```

### Step 4 — Convert XML to JSON

```bash
python datas/src/orphadata_xml2json.py
```

JSON files are saved to `datas/json_data/`.

**Final output:** 5 JSON files, ~147MB total.

---

## Source 2: HPO — Human Phenotype Ontology

Download the ontology file using its permanent URL:

**PowerShell:**
```powershell
Invoke-WebRequest -Uri "http://purl.obolibrary.org/obo/hp.obo" -OutFile "hp.obo"
```
> **Note:** `phenotype.hpoa` (disease-symptom annotations) is not separately needed — this information is already covered by Orphanet `en_product4.xml`.

**Final output:** `hp.obo`, ~10MB.

---

## Source 3: ClinVar

### Step 1 — Download

**PowerShell:**
```powershell
Invoke-WebRequest -Uri "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz" -OutFile "variant_summary.txt.gz"
```

**bash:**
```bash
curl -O https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz
```

File size: ~435MB compressed.

### Step 2 — Filter

Run `filter_clinvar.py` in the same folder as the downloaded file.

```bash
python filter_clinvar.py
```

Takes 3–5 minutes. After confirming `clinvar_filtered.json` looks correct, delete the raw file:

**PowerShell:**
```powershell
Remove-Item variant_summary.txt.gz
```

**bash:**
```bash
rm variant_summary.txt.gz
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

> This runs for 2–3 hours. Leave it overnight. It saves a checkpoint every 100 diseases so it won't lose progress if interrupted.

**Final output:** `pubmed_abstracts.json`, ~150–250MB.

---

## Source 5: LabQAR — Lab Reference Ranges

```bash
git clone https://github.com/balubhasuran/LabQAR.git
```

No processing needed. The dataset inside contains 550 lab test reference ranges across 363 unique tests, LOINC-mapped, with specimen types and gender/age variations.

**Final output:** CSV/JSON files inside the `LabQAR/` folder, ~1MB.

---

## Final Data Checklist

```
File/Folder                     Size (approx)    Source
────────────────────────────────────────────────────────
en_product1.json                ~25MB            Orphanet
en_product4.json                ~20MB            Orphanet
en_product6.json                ~10MB            Orphanet
en_product9_ages.json           ~3MB             Orphanet
en_product9_prev.json           ~7MB             Orphanet
hp.obo                          ~10MB            HPO
clinvar_filtered.json           ~50-80MB         ClinVar
pubmed_abstracts.json           ~150-250MB       PubMed
LabQAR/                         ~1MB             LabQAR
────────────────────────────────────────────────────────
Total                           ~280-400MB
```

---

## Notes

- All data sources are free and open access. No payment required.
- Orphanet data is licensed under CC BY 4.0 — attribution required.
- ClinVar and PubMed are NCBI resources in the public domain.
- HPO is licensed under CC BY 4.0.
- LabQAR is a research dataset — cite the original paper if publishing.
- Re-run downloads periodically — Orphanet updates twice a year (July/December), ClinVar and HPO update monthly.