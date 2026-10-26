#!/usr/bin/env python3
"""Build a sanitized, read-only snapshot for the fixed eight reviewed products.

Only fresh Rakuten API search output is accepted. Never infer inventory from
an active listing or a valid affiliate URL. Never approve products for posting.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, parse_qs

review = json.loads(Path("research/claude-candidate-url-review.json").read_text(encoding="utf-8"))
raw = json.loads(Path("research/rakuten-candidates.json").read_text(encoding="utf-8"))
index = {p.get("item_code"): p for p in raw.get("products", [])}
results = []
for entry in review["products"]:
    code = entry["item_code"]
    item = index.get(code)
    price = item.get("price_jpy") if item else None
    price_ok = type(price) in (int, float) and price > 0
    page = item.get("merchant_url") if item else None
    page_match = bool(page and page.rstrip("/") == entry["merchant_url"].rstrip("/"))
    link = item.get("affiliate_url") if item else None
    link_valid = False
    if isinstance(link, str):
        parsed = urlparse(link)
        if parsed.scheme == "https" and parsed.hostname == "hb.afl.rakuten.co.jp":
            pc = parse_qs(parsed.query).get("pc", [""])[0]
            link_valid = pc.rstrip("/") == entry["merchant_url"].rstrip("/")
    results.append({
        "item_code": code,
        "api_found": bool(item),
        "api_product_name": item.get("name") if item else None,
        "api_shop_name": item.get("shop_name") if item else None,
        "price_jpy": price if price_ok else None,
        "price_verified_from_fresh_api": bool(price_ok),
        "merchant_page_matches_review": page_match,
        "affiliate_url_present": bool(link),
        "affiliate_url_target_matches_review": link_valid,
        "stock_status": "unknown_not_provided_by_this_api_snapshot",
        "stock_verified": False,
        "approved_for_posting": False,
    })
out = {
    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    "brand": review["brand"],
    "source": "fresh_rakuten_ichiba_api_search",
    "status": "research_only_not_posting_approved",
    "summary": {
        "total": len(results),
        "api_found": sum(x["api_found"] for x in results),
        "price_verified": sum(x["price_verified_from_fresh_api"] for x in results),
        "merchant_url_matched": sum(x["merchant_page_matches_review"] for x in results),
        "affiliate_target_matched": sum(x["affiliate_url_target_matches_review"] for x in results),
        "stock_verified": 0,
        "approved": 0,
    },
    "products": results,
}
dest = Path("research/rakuten-eight-current-snapshot.json")
dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("Snapshot:", out["summary"])
