import json
import os

FILES = {
    "product1": "../datas/orpha_json/en_product1.json",
    "product4": "../datas/orpha_json/en_product4.json",
    "product6": "../datas/orpha_json/en_product6.json",
    "product9": "../datas/orpha_json/en_product9_ages.json",
    "hp":       "../datas/hp.json",
    "clinvar":  "../datas/clinvar_filtered.json",
}

def inspect(name, path):
    print(f"\n{'='*60}")
    print(f"FILE : {name} — {path}")
    size = os.path.getsize(path) / 1024 / 1024
    print(f"SIZE : {size:.1f} MB")

    with open(path, encoding="utf-8") as f:
        first_chars = f.read(3)

    # Detect format
    with open(path, encoding="utf-8") as f:
        if first_chars.strip().startswith("["):
            data = json.load(f)
            print(f"FORMAT : JSON array, length {len(data)}")
            if data and isinstance(data[0], dict):
                print(f"KEYS   : {list(data[0].keys())}")
                print(f"SAMPLE :\n{json.dumps(data[0], indent=2)[:600]}")

        elif first_chars.strip().startswith("{"):
            # Could be NDJSON or single object
            content = f.read()
            lines = [l.strip() for l in content.splitlines() if l.strip()]
            try:
                single = json.loads(content)
                print(f"FORMAT : Single JSON object")
                print(f"KEYS   : {list(single.keys())[:8]}")
                # drill into first meaningful key
                for k, v in single.items():
                    if isinstance(v, list) and v:
                        print(f"  '{k}' is list of {len(v)}, first item:")
                        print(f"  {json.dumps(v[0], indent=4)[:400]}")
                        break
                    elif isinstance(v, dict):
                        print(f"  '{k}' is dict, keys: {list(v.keys())[:6]}")
                        break
            except json.JSONDecodeError:
                # NDJSON
                data_lines = []
                for line in lines:
                    try:
                        obj = json.loads(line)
                        if "index" not in obj and "_index" not in obj:
                            data_lines.append(obj)
                    except:
                        continue
                print(f"FORMAT : NDJSON, {len(data_lines)} data lines")
                if data_lines:
                    print(f"KEYS   : {list(data_lines[0].keys())}")
                    print(f"SAMPLE :\n{json.dumps(data_lines[0], indent=2)[:600]}")

for name, path in FILES.items():
    if os.path.exists(path):
        inspect(name, path)
    else:
        print(f"\nNOT FOUND: {path}")