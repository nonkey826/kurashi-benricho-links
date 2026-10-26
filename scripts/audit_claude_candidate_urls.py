#!/usr/bin/env python3
"""Offline structural URL audit of Claude candidate JSON. Never approves posting."""
import argparse
import json
import urllib.parse
from pathlib import Path

def audit(item):
    code = item.get("item_code", "")
    merchant = item.get("merchant_url", "")
    affiliate = item.get("affiliate_url", "")
    problems = []
    if not isinstance(code, str) or ":" not in code:
        problems.append("invalid_item_code")
    shop = code.split(":", 1)[0] if isinstance(code, str) else ""
    if not isinstance(merchant, str):
        merchant = ""
    parsed = urllib.parse.urlparse(merchant)
    if parsed.scheme != "https":
        problems.append("invalid_url_scheme")
    if parsed.hostname == "hb.afl.rakuten.co.jp":
        extracted = urllib.parse.parse_qs(parsed.query).get("pc", [""])[0]
    elif parsed.hostname == "item.rakuten.co.jp":
        extracted = merchant
    else:
        extracted = ""
        problems.append("unrecognized_merchant_url")
    target = urllib.parse.urlparse(extracted)
    segments = [s for s in target.path.split("/") if s]
    if target.scheme != "https" or target.hostname != "item.rakuten.co.jp" or len(segments) < 2 or segments[0] != shop:
        problems.append("merchant_page_structure_mismatch")
        extracted = None
    if not isinstance(affiliate, str) or urllib.parse.urlparse(affiliate).hostname != "hb.afl.rakuten.co.jp":
        problems.append("affiliate_url_unverified_or_missing")
    if merchant == affiliate:
        problems.append("merchant_url_is_affiliate_redirect")
    return {"item_code": code, "canonical_page_url": extracted,
            "structural_checks_passed": not problems, "issues": problems,
            "page_content_verified": False, "affiliate_destination_verified": False,
            "approved_for_posting": False}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", default="research/claude-product-candidates.json")
    parser.add_argument("--output", default="research/claude-candidate-url-audit.json")
    args = parser.parse_args()
    source = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = {"status": "offline_url_structure_only_not_approved_for_posting",
              "products": [audit(p) for p in source.get("products", [])]}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Audited {len(result['products'])} candidates; 0 approved for posting.")

if __name__ == "__main__":
    main()
