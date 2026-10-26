#!/usr/bin/env python3
"""Convert an AI-reviewed candidate file to an explicitly unapproved Claude handoff.

Offline only. Never approves products or calls APIs. No posting side effects.
"""
import json
import sys
import urllib.parse
from pathlib import Path

def normalize(row):
    item = dict(row)
    code = item.get("item_code", "")
    original = item.get("merchant_url", "")
    parsed = urllib.parse.urlparse(original if isinstance(original, str) else "")
    if parsed.hostname == "hb.afl.rakuten.co.jp":
        page = urllib.parse.parse_qs(parsed.query).get("pc", [""])[0]
    else:
        page = original
    dest = urllib.parse.urlparse(page if isinstance(page, str) else "")
    parts = [p for p in dest.path.split("/") if p]
    valid = (isinstance(code, str) and ":" in code and
             dest.scheme == "https" and dest.hostname == "item.rakuten.co.jp" and
             len(parts) >= 2 and parts[0] == code.split(":", 1)[0])
    item["merchant_url"] = page if valid else None
    item["url_structure_checked"] = valid
    item["verification_status"] = "url_structure_only_not_merchant_or_affiliate_verified"
    item["merchant_page_content_verified"] = False
    item["affiliate_destination_verified"] = False
    item["approved_for_posting"] = False
    return item

def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python3 scripts/build_claude_review_handoff.py INPUT_JSON OUTPUT_JSON")
    source = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if source.get("brand") != "暮らしの便利帖｜大人の愛用品":
        raise SystemExit("Brand mismatch: refusing to create handoff")
    rows = source.get("products")
    if not isinstance(rows, list):
        raise SystemExit("Invalid product list")
    output = dict(source)
    output["status"] = "review_only_not_approved_for_posting"
    output["products"] = [normalize(p) for p in rows if isinstance(p, dict)]
    path = Path(sys.argv[2])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Review-only handoff: {len(output['products'])} candidates, zero approved")

if __name__ == "__main__":
    main()
