#!/usr/bin/env python3
"""Fetch genuine Rakuten Ichiba listings. Standalone, never runs in posting automation.

Requires RAKUTEN_APPLICATION_ID and RAKUTEN_ACCESS_KEY. Optional
RAKUTEN_AFFILIATE_ID. Manual execution only; does not publish products.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUTPUT = Path("research/rakuten-candidates.json")
ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
QUERIES = ["キッチン 便利グッズ", "収納 便利", "掃除 時短"]

def fetch(query):
    params = {"applicationId": os.environ["RAKUTEN_APPLICATION_ID"],
              "keyword": query, "hits": 10, "format": "json"}
    if os.getenv("RAKUTEN_ACCESS_KEY"):
        params["accessKey"] = os.environ["RAKUTEN_ACCESS_KEY"]
    if os.getenv("RAKUTEN_AFFILIATE_ID"):
        params["affiliateId"] = os.environ["RAKUTEN_AFFILIATE_ID"]
    req = urllib.request.Request(ENDPOINT + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": "KurashiBenrichoResearch/1.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)

def merchant_page(item_url, item_code):
    """Extract Rakuten item page from API URL without claiming page verification."""
    parsed = urllib.parse.urlparse(item_url)
    if parsed.hostname == "item.rakuten.co.jp":
        page = item_url
    elif parsed.hostname == "hb.afl.rakuten.co.jp":
        page = urllib.parse.parse_qs(parsed.query).get("pc", [""])[0]
    else:
        return None
    dest = urllib.parse.urlparse(page)
    if dest.scheme != "https" or dest.hostname != "item.rakuten.co.jp":
        return None
    shop = str(item_code).split(":", 1)[0]
    parts = [x for x in dest.path.split("/") if x]
    if len(parts) < 2 or parts[0] != shop:
        return None
    return page

def main():
    if not os.getenv("RAKUTEN_APPLICATION_ID") or not os.getenv("RAKUTEN_ACCESS_KEY"):
        sys.exit("RAKUTEN_APPLICATION_ID and RAKUTEN_ACCESS_KEY are required")
    items = {}
    for query in QUERIES:
        for row in fetch(query).get("Items", []):
            item = row.get("Item", row)
            code = item.get("itemCode")
            url = item.get("itemUrl")
            if not code or not isinstance(url, str):
                continue
            page = merchant_page(url, code)
            if not page:
                continue
            items[code] = {
                "item_code": code, "name": item.get("itemName"),
                "price_jpy": item.get("itemPrice"), "merchant_url": page,
                "affiliate_url": item.get("affiliateUrl") if os.getenv("RAKUTEN_AFFILIATE_ID") else None,
                "review_count": item.get("reviewCount"), "review_average": item.get("reviewAverage"),
                "shop_name": item.get("shopName"), "source": "rakuten_ichiba_api",
                "sales_evidence": "not_verified"
            }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({"updated_at": datetime.now(timezone.utc).isoformat(),
        "status": "raw_api_candidates_not_sales_verified", "products": list(items.values())},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(items)} API-sourced candidates (not yet sales verified).")

if __name__ == "__main__":
    main()
