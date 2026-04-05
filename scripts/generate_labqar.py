import json
import os

os.makedirs("data/raw", exist_ok=True)

# ── COMPLETE LAB REFERENCE DATABASE ───────────────────────────────────────────
# Covers all major panels used in rare disease diagnosis:
# metabolic, haematology, liver, renal, endocrine, cardiac,
# inflammatory, lysosomal enzymes, and genetic markers
# ──────────────────────────────────────────────────────────────────────────────

LAB_REFERENCE = [

    # ── COMPLETE BLOOD COUNT ──────────────────────────────────────────────────
    {
        "test": "Haemoglobin",
        "abbreviation": "Hb",
        "panel": "Complete Blood Count",
        "unit": "g/dL",
        "normal_range": {"min": 12.0, "max": 17.5},
        "low_flag": "Anaemia — seen in haemolytic anaemias, sickle cell, thalassaemia, Gaucher disease",
        "high_flag": "Polycythaemia — consider congenital polycythaemia, EPO disorders",
        "critical_low": 7.0,
        "critical_high": 20.0,
        "relevant_rare_diseases": ["Sickle cell disease", "Thalassaemia", "Gaucher disease",
                                    "Diamond-Blackfan anaemia", "Fanconi anaemia"]
    },
    {
        "test": "White Blood Cell Count",
        "abbreviation": "WBC",
        "panel": "Complete Blood Count",
        "unit": "x10^9/L",
        "normal_range": {"min": 4.0, "max": 11.0},
        "low_flag": "Leucopenia — seen in Kostmann syndrome, Chediak-Higashi, Griscelli syndrome",
        "high_flag": "Leucocytosis — infection, leukaemia, or inflammatory conditions",
        "critical_low": 2.0,
        "critical_high": 30.0,
        "relevant_rare_diseases": ["Kostmann syndrome", "Chediak-Higashi syndrome",
                                    "Griscelli syndrome", "Chronic granulomatous disease"]
    },
    {
        "test": "Platelet Count",
        "abbreviation": "PLT",
        "panel": "Complete Blood Count",
        "unit": "x10^9/L",
        "normal_range": {"min": 150, "max": 400},
        "low_flag": "Thrombocytopenia — Wiskott-Aldrich, Gaucher, TAR syndrome, Bernard-Soulier",
        "high_flag": "Thrombocytosis — reactive or essential thrombocythaemia",
        "critical_low": 50,
        "critical_high": 1000,
        "relevant_rare_diseases": ["Wiskott-Aldrich syndrome", "Gaucher disease",
                                    "TAR syndrome", "Bernard-Soulier syndrome"]
    },
    {
        "test": "Mean Corpuscular Volume",
        "abbreviation": "MCV",
        "panel": "Complete Blood Count",
        "unit": "fL",
        "normal_range": {"min": 80, "max": 100},
        "low_flag": "Microcytic anaemia — thalassaemia, iron deficiency, sideroblastic anaemia",
        "high_flag": "Macrocytic anaemia — cobalamin/folate deficiency, Pearson syndrome",
        "critical_low": None,
        "critical_high": None,
        "relevant_rare_diseases": ["Thalassaemia", "Sideroblastic anaemia",
                                    "Pearson syndrome", "Orotic aciduria"]
    },

    # ── METABOLIC / LIVER PANEL ───────────────────────────────────────────────
    {
        "test": "Alanine Aminotransferase",
        "abbreviation": "ALT",
        "panel": "Liver Function",
        "unit": "U/L",
        "normal_range": {"min": 7, "max": 56},
        "low_flag": "Not clinically significant",
        "high_flag": "Hepatocellular damage — Wilson disease, tyrosinaemia, Gaucher, NAFLD",
        "critical_low": None,
        "critical_high": 500,
        "relevant_rare_diseases": ["Wilson disease", "Tyrosinaemia type 1",
                                    "Gaucher disease", "Alpha-1 antitrypsin deficiency"]
    },
    {
        "test": "Aspartate Aminotransferase",
        "abbreviation": "AST",
        "panel": "Liver Function",
        "unit": "U/L",
        "normal_range": {"min": 10, "max": 40},
        "low_flag": "Not clinically significant",
        "high_flag": "Liver or muscle damage — Wilson disease, Pompe, muscular dystrophies",
        "critical_low": None,
        "critical_high": 500,
        "relevant_rare_diseases": ["Wilson disease", "Pompe disease",
                                    "Duchenne muscular dystrophy", "Tyrosinaemia"]
    },
    {
        "test": "Alkaline Phosphatase",
        "abbreviation": "ALP",
        "panel": "Liver Function",
        "unit": "U/L",
        "normal_range": {"min": 44, "max": 147},
        "low_flag": "Hypophosphatasia — rare inborn error of bone metabolism",
        "high_flag": "Cholestatic liver disease, bone disease, Gaucher, Niemann-Pick",
        "critical_low": None,
        "critical_high": None,
        "relevant_rare_diseases": ["Hypophosphatasia", "Gaucher disease",
                                    "Niemann-Pick disease", "Alagille syndrome"]
    },
    {
        "test": "Gamma-Glutamyl Transferase",
        "abbreviation": "GGT",
        "panel": "Liver Function",
        "unit": "U/L",
        "normal_range": {"min": 9, "max": 48},
        "low_flag": "Not clinically significant",
        "high_flag": "Cholestasis, bile duct disease — Alagille, PFIC, alpha-1 antitrypsin",
        "critical_low": None,
        "critical_high": None,
        "relevant_rare_diseases": ["Alagille syndrome", "Progressive familial intrahepatic cholestasis",
                                    "Alpha-1 antitrypsin deficiency"]
    },
    {
        "test": "Total Bilirubin",
        "abbreviation": "TBIL",
        "panel": "Liver Function",
        "unit": "mg/dL",
        "normal_range": {"min": 0.1, "max": 1.2},
        "low_flag": "Not clinically significant",
        "high_flag": "Jaundice — haemolytic anaemias, Gilbert, Crigler-Najjar, Dubin-Johnson",
        "critical_low": None,
        "critical_high": 15.0,
        "relevant_rare_diseases": ["Crigler-Najjar syndrome", "Dubin-Johnson syndrome",
                                    "Gilbert syndrome", "Rotor syndrome"]
    },

    # ── RENAL PANEL ───────────────────────────────────────────────────────────
    {
        "test": "Creatinine",
        "abbreviation": "Cr",
        "panel": "Renal Function",
        "unit": "mg/dL",
        "normal_range": {"min": 0.6, "max": 1.2},
        "low_flag": "Low muscle mass",
        "high_flag": "Renal impairment — Fabry disease, cystinosis, nephronophthisis",
        "critical_low": None,
        "critical_high": 10.0,
        "relevant_rare_diseases": ["Fabry disease", "Cystinosis", "Nephronophthisis",
                                    "Alport syndrome", "Primary hyperoxaluria"]
    },
    {
        "test": "Blood Urea Nitrogen",
        "abbreviation": "BUN",
        "panel": "Renal Function",
        "unit": "mg/dL",
        "normal_range": {"min": 7, "max": 20},
        "low_flag": "Liver disease, malnutrition",
        "high_flag": "Renal failure, urea cycle disorders",
        "critical_low": None,
        "critical_high": 100,
        "relevant_rare_diseases": ["Urea cycle disorders", "OTC deficiency",
                                    "Citrullinaemia", "Argininosuccinic aciduria"]
    },
    {
        "test": "Uric Acid",
        "abbreviation": "UA",
        "panel": "Renal Function",
        "unit": "mg/dL",
        "normal_range": {"min": 2.4, "max": 7.0},
        "low_flag": "Xanthinuria, Molybdenum cofactor deficiency",
        "high_flag": "Gout, Lesch-Nyhan syndrome, glycogen storage diseases",
        "critical_low": None,
        "critical_high": None,
        "relevant_rare_diseases": ["Lesch-Nyhan syndrome", "Glycogen storage disease type I",
                                    "Xanthinuria", "Molybdenum cofactor deficiency"]
    },

    # ── METABOLIC / ENZYME PANEL ──────────────────────────────────────────────
    {
        "test": "Creatine Kinase",
        "abbreviation": "CK",
        "panel": "Muscle Enzymes",
        "unit": "U/L",
        "normal_range": {"min": 22, "max": 198},
        "low_flag": "Not clinically significant",
        "high_flag": "Muscle damage — Duchenne/Becker MD, LGMD, Pompe, McArdle, myositis",
        "critical_low": None,
        "critical_high": 10000,
        "relevant_rare_diseases": ["Duchenne muscular dystrophy", "Becker muscular dystrophy",
                                    "Limb-girdle muscular dystrophy", "Pompe disease",
                                    "McArdle disease", "Myotonic dystrophy"]
    },
    {
        "test": "Lactate Dehydrogenase",
        "abbreviation": "LDH",
        "panel": "Muscle Enzymes",
        "unit": "U/L",
        "normal_range": {"min": 140, "max": 280},
        "low_flag": "Not clinically significant",
        "high_flag": "Haemolysis, tissue damage — haemolytic anaemias, Gaucher, lymphoma",
        "critical_low": None,
        "critical_high": None,
        "relevant_rare_diseases": ["Gaucher disease", "Sickle cell disease",
                                    "Haemolytic anaemias", "Glycogen storage diseases"]
    },
    {
        "test": "Ammonia",
        "abbreviation": "NH3",
        "panel": "Metabolic",
        "unit": "µmol/L",
        "normal_range": {"min": 9, "max": 33},
        "low_flag": "Not clinically significant",
        "high_flag": "Urea cycle disorders, organic acidaemias, fatty acid oxidation defects",
        "critical_low": None,
        "critical_high": 150,
        "relevant_rare_diseases": ["OTC deficiency", "Citrullinaemia", "Argininaemia",
                                    "Propionic acidaemia", "Methylmalonic acidaemia",
                                    "MSUD", "Glutaric aciduria"]
    },
    {
        "test": "Lactate",
        "abbreviation": "Lac",
        "panel": "Metabolic",
        "unit": "mmol/L",
        "normal_range": {"min": 0.5, "max": 2.2},
        "low_flag": "Not clinically significant",
        "high_flag": "Mitochondrial disorders, PDH deficiency, glycogen storage, MELAS",
        "critical_low": None,
        "critical_high": 5.0,
        "relevant_rare_diseases": ["MELAS", "Leigh syndrome", "Pyruvate dehydrogenase deficiency",
                                    "Glycogen storage disease type I", "Mitochondrial disorders"]
    },
    {
        "test": "Pyruvate",
        "abbreviation": "Pyr",
        "panel": "Metabolic",
        "unit": "µmol/L",
        "normal_range": {"min": 40, "max": 130},
        "low_flag": "Not clinically significant",
        "high_flag": "PDH deficiency, mitochondrial disorders — check lactate:pyruvate ratio",
        "critical_low": None,
        "critical_high": None,
        "relevant_rare_diseases": ["Pyruvate dehydrogenase deficiency",
                                    "Pyruvate carboxylase deficiency", "MELAS"]
    },

    # ── LYSOSOMAL ENZYME ASSAYS ───────────────────────────────────────────────
    {
        "test": "Acid Alpha-Glucosidase",
        "abbreviation": "GAA",
        "panel": "Lysosomal Enzymes",
        "unit": "nmol/hr/mg",
        "normal_range": {"min": 10.0, "max": 70.0},
        "low_flag": "Pompe disease (Glycogen storage disease type II) — confirm with GAA gene sequencing",
        "high_flag": "Not clinically significant",
        "critical_low": 1.0,
        "critical_high": None,
        "relevant_rare_diseases": ["Pompe disease"]
    },
    {
        "test": "Beta-Glucocerebrosidase",
        "abbreviation": "GBA",
        "panel": "Lysosomal Enzymes",
        "unit": "nmol/hr/mg",
        "normal_range": {"min": 8.0, "max": 30.0},
        "low_flag": "Gaucher disease — confirm with GBA gene sequencing",
        "high_flag": "Not clinically significant",
        "critical_low": 2.0,
        "critical_high": None,
        "relevant_rare_diseases": ["Gaucher disease"]
    },
    {
        "test": "Alpha-Galactosidase A",
        "abbreviation": "GLA",
        "panel": "Lysosomal Enzymes",
        "unit": "nmol/hr/mg",
        "normal_range": {"min": 25.0, "max": 90.0},
        "low_flag": "Fabry disease — confirm with GLA gene sequencing (males most affected)",
        "high_flag": "Not clinically significant",
        "critical_low": 5.0,
        "critical_high": None,
        "relevant_rare_diseases": ["Fabry disease"]
    },
    {
        "test": "Sphingomyelinase",
        "abbreviation": "SMPD1",
        "panel": "Lysosomal Enzymes",
        "unit": "nmol/hr/mg",
        "normal_range": {"min": 20.0, "max": 80.0},
        "low_flag": "Niemann-Pick disease type A/B",
        "high_flag": "Not clinically significant",
        "critical_low": None,
        "critical_high": None,
        "relevant_rare_diseases": ["Niemann-Pick disease type A", "Niemann-Pick disease type B"]
    },
    {
        "test": "Hexosaminidase A",
        "abbreviation": "HexA",
        "panel": "Lysosomal Enzymes",
        "unit": "nmol/hr/mg",
        "normal_range": {"min": 400, "max": 1200},
        "low_flag": "Tay-Sachs disease — HexA deficient with normal HexB",
        "high_flag": "Not clinically significant",
        "critical_low": None,
        "critical_high": None,
        "relevant_rare_diseases": ["Tay-Sachs disease", "GM2 gangliosidosis"]
    },

    # ── ENDOCRINE PANEL ───────────────────────────────────────────────────────
    {
        "test": "Thyroid Stimulating Hormone",
        "abbreviation": "TSH",
        "panel": "Endocrine",
        "unit": "mIU/L",
        "normal_range": {"min": 0.4, "max": 4.0},
        "low_flag": "Hyperthyroidism — consider MEN syndromes if familial",
        "high_flag": "Hypothyroidism — consider Pendred syndrome, congenital hypothyroidism",
        "critical_low": 0.01,
        "critical_high": 10.0,
        "relevant_rare_diseases": ["Pendred syndrome", "Congenital hypothyroidism",
                                    "Multiple endocrine neoplasia"]
    },
    {
        "test": "Cortisol (morning)",
        "abbreviation": "Cort",
        "panel": "Endocrine",
        "unit": "µg/dL",
        "normal_range": {"min": 6.2, "max": 19.4},
        "low_flag": "Adrenal insufficiency — congenital adrenal hyperplasia, Addison disease",
        "high_flag": "Cushing syndrome — consider MEN1, ACTH-dependent causes",
        "critical_low": 2.0,
        "critical_high": None,
        "relevant_rare_diseases": ["Congenital adrenal hyperplasia", "Addison disease",
                                    "X-linked adrenoleukodystrophy"]
    },

    # ── AMINO ACIDS / ORGANIC ACIDS (NBS PANEL) ───────────────────────────────
    {
        "test": "Phenylalanine",
        "abbreviation": "Phe",
        "panel": "Amino Acids",
        "unit": "µmol/L",
        "normal_range": {"min": 35, "max": 90},
        "low_flag": "Not clinically significant",
        "high_flag": "Phenylketonuria (PKU), hyperphenylalaninaemia, BH4 deficiency",
        "critical_low": None,
        "critical_high": 600,
        "relevant_rare_diseases": ["Phenylketonuria", "Hyperphenylalaninaemia",
                                    "BH4 deficiency", "DHPR deficiency"]
    },
    {
        "test": "Leucine/Isoleucine/Valine (BCAA)",
        "abbreviation": "BCAA",
        "panel": "Amino Acids",
        "unit": "µmol/L",
        "normal_range": {"min": 50, "max": 200},
        "low_flag": "Not clinically significant",
        "high_flag": "Maple syrup urine disease (MSUD) — sweet-smelling urine, encephalopathy",
        "critical_low": None,
        "critical_high": 500,
        "relevant_rare_diseases": ["Maple syrup urine disease"]
    },
    {
        "test": "Homocysteine",
        "abbreviation": "Hcy",
        "panel": "Amino Acids",
        "unit": "µmol/L",
        "normal_range": {"min": 5, "max": 15},
        "low_flag": "Not clinically significant",
        "high_flag": "Homocystinuria, CBS deficiency, MTHFR deficiency, cobalamin disorders",
        "critical_low": None,
        "critical_high": 100,
        "relevant_rare_diseases": ["Homocystinuria", "CBS deficiency",
                                    "Cobalamin C disease", "MTHFR deficiency"]
    },
    {
        "test": "Tyrosine",
        "abbreviation": "Tyr",
        "panel": "Amino Acids",
        "unit": "µmol/L",
        "normal_range": {"min": 30, "max": 100},
        "low_flag": "Not clinically significant",
        "high_flag": "Tyrosinaemia type 1/2/3 — liver disease, corneal ulcers, neurological crises",
        "critical_low": None,
        "critical_high": 500,
        "relevant_rare_diseases": ["Tyrosinaemia type 1", "Tyrosinaemia type 2",
                                    "Tyrosinaemia type 3"]
    },

    # ── COPPER / METAL METABOLISM ─────────────────────────────────────────────
    {
        "test": "Serum Copper",
        "abbreviation": "Cu",
        "panel": "Trace Metals",
        "unit": "µg/dL",
        "normal_range": {"min": 70, "max": 140},
        "low_flag": "Menkes disease, copper deficiency",
        "high_flag": "Wilson disease — check urinary copper and caeruloplasmin",
        "critical_low": None,
        "critical_high": None,
        "relevant_rare_diseases": ["Wilson disease", "Menkes disease"]
    },
    {
        "test": "Caeruloplasmin",
        "abbreviation": "Cp",
        "panel": "Trace Metals",
        "unit": "mg/dL",
        "normal_range": {"min": 20, "max": 60},
        "low_flag": "Wilson disease, Menkes disease, acaeruloplasminaemia",
        "high_flag": "Acute phase reaction — not specific",
        "critical_low": 10.0,
        "critical_high": None,
        "relevant_rare_diseases": ["Wilson disease", "Menkes disease",
                                    "Acaeruloplasminaemia"]
    },
    {
        "test": "24-hr Urinary Copper",
        "abbreviation": "uCu",
        "panel": "Trace Metals",
        "unit": "µg/24hr",
        "normal_range": {"min": 3, "max": 35},
        "low_flag": "Not clinically significant",
        "high_flag": "Wilson disease — >100 µg/24hr is diagnostic threshold",
        "critical_low": None,
        "critical_high": None,
        "relevant_rare_diseases": ["Wilson disease"]
    },

    # ── INFLAMMATORY / IMMUNE ─────────────────────────────────────────────────
    {
        "test": "C-Reactive Protein",
        "abbreviation": "CRP",
        "panel": "Inflammatory",
        "unit": "mg/L",
        "normal_range": {"min": 0, "max": 10},
        "low_flag": "Not clinically significant",
        "high_flag": "Inflammation, autoinflammatory diseases — FMF, CAPS, TRAPS, HIDS",
        "critical_low": None,
        "critical_high": None,
        "relevant_rare_diseases": ["Familial Mediterranean fever", "CAPS",
                                    "TRAPS", "Hyper-IgD syndrome"]
    },
    {
        "test": "Erythrocyte Sedimentation Rate",
        "abbreviation": "ESR",
        "panel": "Inflammatory",
        "unit": "mm/hr",
        "normal_range": {"min": 0, "max": 20},
        "low_flag": "Not clinically significant",
        "high_flag": "Chronic inflammation — periodic fever syndromes, vasculitides",
        "critical_low": None,
        "critical_high": None,
        "relevant_rare_diseases": ["Familial Mediterranean fever", "TRAPS",
                                    "Systemic vasculitides"]
    },
    {
        "test": "Immunoglobulin G",
        "abbreviation": "IgG",
        "panel": "Immunology",
        "unit": "mg/dL",
        "normal_range": {"min": 700, "max": 1600},
        "low_flag": "Hypogammaglobulinaemia — XLA, CVID, IgG subclass deficiency",
        "high_flag": "Hypergammaglobulinaemia — chronic infection, ALPS, autoimmune",
        "critical_low": 200,
        "critical_high": None,
        "relevant_rare_diseases": ["X-linked agammaglobulinaemia", "CVID",
                                    "Selective IgA deficiency", "ALPS"]
    },

    # ── COAGULATION ───────────────────────────────────────────────────────────
    {
        "test": "Prothrombin Time",
        "abbreviation": "PT",
        "panel": "Coagulation",
        "unit": "seconds",
        "normal_range": {"min": 11, "max": 13.5},
        "low_flag": "Not clinically significant",
        "high_flag": "Clotting factor deficiency, liver disease, warfarin, VKD",
        "critical_low": None,
        "critical_high": 30,
        "relevant_rare_diseases": ["Haemophilia A", "Haemophilia B",
                                    "Factor VII deficiency", "Vitamin K-dependent clotting factor deficiency"]
    },
    {
        "test": "APTT",
        "abbreviation": "APTT",
        "panel": "Coagulation",
        "unit": "seconds",
        "normal_range": {"min": 25, "max": 35},
        "low_flag": "Not clinically significant",
        "high_flag": "Haemophilia A/B, von Willebrand disease, factor deficiency",
        "critical_low": None,
        "critical_high": 70,
        "relevant_rare_diseases": ["Haemophilia A", "Haemophilia B",
                                    "Von Willebrand disease", "Factor XI deficiency"]
    },
    {
        "test": "Fibrinogen",
        "abbreviation": "Fib",
        "panel": "Coagulation",
        "unit": "mg/dL",
        "normal_range": {"min": 200, "max": 400},
        "low_flag": "Afibrinogenaemia, hypofibrinogenaemia, DIC",
        "high_flag": "Acute phase response, thrombosis risk",
        "critical_low": 100,
        "critical_high": None,
        "relevant_rare_diseases": ["Congenital afibrinogenaemia",
                                    "Congenital hypofibrinogenaemia"]
    },
]

# ── SAVE ──────────────────────────────────────────────────────────────────────
output_path = "data/raw/lab_reference.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(LAB_REFERENCE, f, indent=2, ensure_ascii=False)

print(f"Saved {len(LAB_REFERENCE)} lab tests to {output_path}")

# Summary by panel
from collections import Counter
panels = Counter(t["panel"] for t in LAB_REFERENCE)
print("\nTests per panel:")
for panel, count in sorted(panels.items(), key=lambda x: -x[1]):
    print(f"  {panel:<30} {count} tests")