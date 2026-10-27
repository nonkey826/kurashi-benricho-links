#!/usr/bin/env python3
"""Manual, research-only product evaluation; no publishing."""
import json
import os
import sys
import urllib.request
from pathlib import Path


def discover_new():
    from datetime import datetime, timezone
    raw=json.loads(Path("research/rakuten-candidates.json").read_text())
    dest=Path("research/claude-evaluated-candidates.json")
    saved=json.loads(dest.read_text())
    known={x["item_code"] for x in saved["products"]}
    new=[]
    for x in raw["products"]:
        try:
            if (x["item_code"] not in known and 1000<=int(x["price_jpy"])<=6000
                and int(x["review_count"])>=100 and float(x["review_average"])>=4.2
                and x.get("name") and str(x.get("merchant_url","")).startswith("https://item.rakuten.co.jp/")):
                new.append(x)
        except (KeyError,ValueError,TypeError):
            continue
    new.sort(key=lambda x:-int(x["review_count"]))
    new=new[:5]
    if not new:
        print("No new eligible products; OpenAI not called")
        return
    facts=[{"item_code":x["item_code"],"name":x["name"],"price_jpy":x["price_jpy"],
            "review_count":x["review_count"],"review_average":x["review_average"],
            "description":(x.get("item_caption") or "")[:900]} for x in new]
    prompt=("Evaluate genuine Rakuten products for women aged 40-60 using only supplied facts. "
            "Score evidence readiness, not sales prediction. Never approve posting. "
            "Return JSON object products array with exact item_codes; each must contain item_code, "
            "evidence_readiness_score (integer 0-100), missing_evidence (array), "
            "target_fit_hypothesis (Japanese), evidence_based_reason (Japanese), risks (Japanese). "
            "Do not invent claims. Data: ")+json.dumps(facts,ensure_ascii=False)
    payload={"model":"gpt-4.1-mini","input":prompt,"text":{"format":{"type":"json_object"}},"max_output_tokens":2400}
    req=urllib.request.Request("https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+os.environ["OPENAI_API_KEY"],
        "Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=120) as resp:
        answer=json.load(resp)
    msg=next(x for x in answer["output"] if x["type"]=="message")
    rows=json.loads(next(x["text"] for x in msg["content"] if x["type"]=="output_text"))["products"]
    if (len(rows)!=len(new) or {x.get("item_code") for x in rows}!={x["item_code"] for x in new}
        or any(type(x.get("evidence_readiness_score")) is not int or
               not 0<=x["evidence_readiness_score"]<=100 or
               not isinstance(x.get("missing_evidence"),list) for x in rows)):
        raise ValueError("Invalid evaluation response; no file changes")
    results={x["item_code"]:x for x in rows}
    now=datetime.now(timezone.utc).isoformat()
    for x in new:
        r=results[x["item_code"]]
        saved["products"].append({"item_code":x["item_code"],
            "prior_reviewed_product_name":x["name"],"price_jpy":x["price_jpy"],
            "merchant_url":x["merchant_url"],"shop_name":x.get("shop_name"),
            "review_count_api_snapshot":x["review_count"],"review_average_api_snapshot":x["review_average"],
            "price_source":"Rakuten API snapshot "+now+"; historical, not live",
            "evidence_readiness_score":r["evidence_readiness_score"],
            "missing_evidence":r["missing_evidence"],
            "target_fit_hypothesis":r.get("target_fit_hypothesis"),
            "evidence_based_reason":r.get("evidence_based_reason"),"risks":r.get("risks"),
            "sales_evidence":"unverified","affiliate_attribution":"unverified",
            "current_stock":"unverified","approved_for_posting":False,"posting_decision":"BLOCK"})
    saved["evaluated_count"]=len(saved["products"])
    saved["updated_at"]=now
    dest.write_text(json.dumps(saved,ensure_ascii=False,indent=2)+"\n")
    print("Added",len(new),"new BLOCK candidates")

if __name__=="__main__" and len(sys.argv)>1 and sys.argv[1]=="new_products":
    discover_new()
    sys.exit(0)

source=json.loads(Path("research/claude-readonly-handoff.json").read_text())
raw_path=Path("research/rakuten-candidates.json")
if not raw_path.exists():
    raise SystemExit("Rakuten API data missing; do not evaluate stale or invented product facts")
raw=json.loads(raw_path.read_text(encoding="utf-8"))
index={p["item_code"]:p for p in raw.get("products",[]) if p.get("item_code")}
items=[]
missing=[]
for p in source["products"]:
    live=index.get(p["item_code"])
    if not live or live.get("merchant_url","").rstrip("/")!=p["merchant_url"].rstrip("/"):
        missing.append(p["item_code"])
        continue
    items.append({
        "item_code":p["item_code"],
        "product_name":live.get("name"),
        "price_jpy":live.get("price_jpy"),
        "description":(live.get("item_caption") or "")[:1200] or None,
        "review_count":live.get("review_count"),
        "review_average":live.get("review_average"),
        "availability_code":live.get("api_availability"),
        "sales_count":None,
        "affiliate_rate":None,
    })
if not items:
    raise SystemExit("No matching API products; OpenAI not called")
print("Matched products:",len(items),"Missing or URL mismatch:",missing)
prompt=("Assess these actual Rakuten API products for Japanese women aged 40-60. "
"Use only supplied facts. Distinguish evidence-backed suitability from hypotheses. "
"Reviews are API-reported if present; do not fabricate sales, commissions or rankings. "
"Score evidence readiness, not expected sales. Never approve for posting. "
"Return a JSON object with products array of exactly the supplied number of entries. Each entry: "
"item_code, evidence_readiness_score (integer 0-100), missing_evidence (array), "
"target_fit_hypothesis (Japanese), evidence_based_reason (Japanese), risks (Japanese). "
"Data: ")+json.dumps(items,ensure_ascii=False)
payload={"model":"gpt-4.1-mini","input":prompt,"text":{"format":{"type":"json_object"}},"max_output_tokens":3000}
req=urllib.request.Request("https://api.openai.com/v1/responses",data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+os.environ["OPENAI_API_KEY"],"Content-Type":"application/json"},method="POST")
with urllib.request.urlopen(req,timeout=120) as resp:
    response=json.load(resp)
message=next(x for x in response["output"] if x["type"]=="message")
result=json.loads(next(x["text"] for x in message["content"] if x["type"]=="output_text"))
rows=result["products"]
assert len(rows)==len(items) and {x["item_code"] for x in rows}=={x["item_code"] for x in items}
assert all(type(x["evidence_readiness_score"]) is int and 0<=x["evidence_readiness_score"]<=100 and isinstance(x["missing_evidence"],list) for x in rows)
Path("research/openai-eight-evaluation.json").write_text(json.dumps({"status":"research_only","approved_for_posting":False,"expected_product_count":len(source["products"]),"evaluated_product_count":len(items),"missing_or_url_mismatch_item_codes":missing,"products":rows},ensure_ascii=False,indent=2))
print("Research evaluation saved; posting approvals zero.")
