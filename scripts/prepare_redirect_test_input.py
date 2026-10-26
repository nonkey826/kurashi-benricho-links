#!/usr/bin/env python3
"""Join fresh Rakuten API candidates to the fixed 8-item review list.

Never invent URLs or replace missing items. Produces only ephemeral local input.
"""
import json
from pathlib import Path

review = json.loads(Path("research/claude-candidate-url-review.json").read_text(encoding="utf-8"))
raw = json.loads(Path("research/rakuten-candidates.json").read_text(encoding="utf-8"))
if review.get("brand") != "暮らしの便利帖｜大人の愛用品":
    raise SystemExit("Unexpected brand")
index = {p.get("item_code"): p for p in raw.get("products", [])}
out = []
missing = []
for entry in review.get("products", []):
    code = entry.get("item_code")
    found = index.get(code)
    if not found:
        missing.append(code)
        out.append({"item_code": code, "affiliate_url": None})
    else:
        out.append({"item_code": code, "affiliate_url": found.get("affiliate_url")})
target = Path("research/claude-product-candidates.json")
target.write_text(json.dumps({"brand": review["brand"], "products": out}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Prepared {len(out)} fixed candidate codes; {len(missing)} absent from fresh API results.")
