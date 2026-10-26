#!/usr/bin/env python3
"""Evaluate Rakuten API candidates for Claude handoff; never publish automatically."""
import datetime as dt
import json
import os
import urllib.request
from pathlib import Path

source = json.loads(Path("research/rakuten-candidates.json").read_text(encoding="utf-8"))
rows = source.get("products", [])
eligible = []
for p in rows:
    try:
        price = float(p["price_jpy"])
        reviews = float(p["review_count"])
        rating = float(p["review_average"])
    except (ValueError, TypeError, KeyError):
        continue
    if not (1000 <= price <= 6000 and reviews >= 100 and rating >= 4.2):
        continue
    if not all(isinstance(p.get(k), str) and p[k] for k in ("item_code", "name", "merchant_url")):
        continue
    eligible.append(p)
eligible = eligible[:12]
evaluations = {}
if eligible:
    prompt = (
        "You are evaluating real Rakuten API listings for a Japanese household-goods "
        "affiliate account aimed at women aged 40-60. Assess practical target fit, "
        "purchase motivation, drawbacks and differentiation. Do NOT claim actual sales, "
        "ranking, commission rate, merchant-page verification or link validity. "
        "Return ONLY JSON: {\\\"evaluations\\\":[{\\\"item_code\\\":\\\"...\\\","
        "\\\"score\\\":integer 0-100,\\\"reason\\\":\\\"Japanese brief reason\\\","
        "\\\"risk\\\":\\\"Japanese brief risk\\\"}]}. "
        "Evaluate only supplied item codes; do not invent products. Data: "
        + json.dumps([{"item_code": p["item_code"], "name": p["name"],
                       "price_jpy": p["price_jpy"], "review_count": p["review_count"],
                       "review_average": p["review_average"]} for p in eligible],
                     ensure_ascii=False)
    )
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps({"model": "gpt-4.1-mini", "input": prompt,
                         "max_output_tokens": 1800}).encode(),
        headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
                 "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=90) as resp:
        result = json.load(resp)
    texts = [part.get("text", "") for msg in result.get("output", [])
             if msg.get("type") == "message" for part in msg.get("content", [])
             if part.get("type") == "output_text"]
    parsed = json.loads("\\n".join(texts))
    if not isinstance(parsed.get("evaluations"), list):
        raise SystemExit("Invalid AI evaluation format")
    valid_codes = {p["item_code"] for p in eligible}
    for entry in parsed["evaluations"]:
        if not isinstance(entry, dict) or entry.get("item_code") not in valid_codes:
            continue
        score = entry.get("score")
        if type(score) is not int or not 0 <= score <= 100:
            continue
        if not isinstance(entry.get("reason"), str) or not isinstance(entry.get("risk"), str):
            continue
        evaluations[entry["item_code"]] = entry

out = []
for p in eligible:
    ev = evaluations.get(p["item_code"])
    if not ev:
        continue
    out.append({
        "item_code": p["item_code"], "name": p["name"],
        "price_jpy": p["price_jpy"], "review_count": p["review_count"],
        "review_average": p["review_average"], "merchant_url": p["merchant_url"],
        "affiliate_url": p.get("affiliate_url"),
        "shop_name": p.get("shop_name"),
        "ai_score": ev["score"], "ai_reason": ev["reason"], "ai_risk": ev["risk"],
        "source": "rakuten_ichiba_api",
        "verification_status": "api_data_only_merchant_identity_and_affiliate_not_verified",
        "approved_for_posting": False
    })
out.sort(key=lambda p: p["ai_score"], reverse=True)
payload = {"schema_version": 1, "brand": "暮らしの便利帖｜大人の愛用品",
           "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
           "status": "research_only_not_approved_for_posting",
           "products": out}
target = Path("research/claude-product-candidates.json")
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
print(f"Prepared {len(out)} AI-ranked candidates for manual review; posting prohibited.")
