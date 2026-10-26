#!/usr/bin/env python3
"""Manual, read-only affiliate redirect audit. Never approves posts.

Input: local AI candidate JSON; output: sanitized status report.
No affiliate tracking URLs are logged or stored in the report.
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

INPUT = Path("research/claude-product-candidates.json")
OUTPUT = Path("research/affiliate-redirect-test-report.json")

def check(item):
    code = item.get("item_code", "")
    affiliate = item.get("affiliate_url")
    result = {"item_code": code, "redirect_test": "failed",
              "merchant_destination_matches": False,
              "affiliate_attribution_verified": False,
              "approved_for_posting": False}
    if not isinstance(affiliate, str) or not isinstance(code, str) or ":" not in code:
        result["error"] = "missing_or_invalid_fields"
        return result
    parsed = urllib.parse.urlparse(affiliate)
    if parsed.scheme != "https" or parsed.hostname != "hb.afl.rakuten.co.jp":
        result["error"] = "unexpected_affiliate_host"
        return result
    expected = urllib.parse.parse_qs(parsed.query).get("pc", [""])[0]
    expected_url = urllib.parse.urlparse(expected)
    if expected_url.scheme != "https" or expected_url.hostname != "item.rakuten.co.jp":
        result["error"] = "invalid_expected_merchant_url"
        return result
    shop = code.split(":", 1)[0]
    if not expected_url.path.startswith("/" + shop + "/"):
        result["error"] = "item_code_shop_mismatch"
        return result
    try:
        req = urllib.request.Request(affiliate, headers={"User-Agent": "Mozilla/5.0 (compatible; LinkAudit/1.0)"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            actual = urllib.parse.urlparse(resp.url)
            result["http_status"] = resp.status
            result["final_host"] = actual.hostname
            # Ignore query and fragment: those may include tracking parameters.
            result["merchant_destination_matches"] = (
                actual.scheme == expected_url.scheme and
                actual.hostname == expected_url.hostname and
                actual.path.rstrip("/") == expected_url.path.rstrip("/"))
            result["redirect_test"] = "completed" if result["merchant_destination_matches"] else "destination_mismatch"
    except urllib.error.HTTPError as exc:
        result["error"] = "http_error"
        result["http_status"] = exc.code
    except Exception as exc:
        result["error"] = type(exc).__name__
    return result

def main():
    source = json.loads(INPUT.read_text(encoding="utf-8"))
    if source.get("brand") != "暮らしの便利帖｜大人の愛用品":
        sys.exit("Unexpected brand")
    products = source.get("products", [])
    results = [check(p) for p in products]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({
        "status": "redirect_test_only_not_posting_approval",
        "note": "Successful redirects do not prove affiliate tracking or attribution.",
        "results": results
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Checked {len(results)} URLs; matched destination: {sum(r['merchant_destination_matches'] for r in results)}; posting approved: 0")

if __name__ == "__main__":
    main()
