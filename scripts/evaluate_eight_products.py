#!/usr/bin/env python3
"""Manual, research-only product evaluation; no publishing."""
import json
import os
import urllib.request
from pathlib import Path

source=json.loads(Path("research/claude-readonly-handoff.json").read_text())
items=[{"item_code":p["item_code"],"price_jpy":p["current_price_jpy"],"stock":"unknown","reviews":"unknown","sales":"unknown"} for p in source["products"]]
assert len(items)==8
prompt="Evaluate evidence readiness for eight Japanese household products targeting women aged 40-60. No product titles, sales, review, stock or feature evidence is supplied. Do not invent facts. Respond JSON object with products array of 8 entries each with item_code, evidence_readiness_score integer 0-100, missing_evidence array, and target_fit_hypothesis Japanese text. No posting approvals. Data: "+json.dumps(items,ensure_ascii=False)
payload={"model":"gpt-4.1-mini","input":prompt,"text":{"format":{"type":"json_object"}},"max_output_tokens":3000}
req=urllib.request.Request("https://api.openai.com/v1/responses",data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+os.environ["OPENAI_API_KEY"],"Content-Type":"application/json"},method="POST")
with urllib.request.urlopen(req,timeout=120) as resp:
    response=json.load(resp)
message=next(x for x in response["output"] if x["type"]=="message")
result=json.loads(next(x["text"] for x in message["content"] if x["type"]=="output_text"))
rows=result["products"]
assert len(rows)==8 and {x["item_code"] for x in rows}=={x["item_code"] for x in items}
assert all(type(x["evidence_readiness_score"]) is int and 0<=x["evidence_readiness_score"]<=100 and isinstance(x["missing_evidence"],list) for x in rows)
Path("research/openai-eight-evaluation.json").write_text(json.dumps({"status":"research_only","approved_for_posting":False,"products":rows},ensure_ascii=False,indent=2))
print("Research evaluation saved; posting approvals zero.")
