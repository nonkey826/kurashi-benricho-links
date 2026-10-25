#!/usr/bin/env python3
"""Research product demand with OpenAI web search; never fabricate verification."""
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

OUTPUT = Path("research/threads-products.json")
today = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date().isoformat()
prompt = f"""Today in Japan: {today}. Research products likely to SELL (not merely viral) for Japanese women age 40-60, for 暮らしの便利帖｜大人の愛用品.
Focus: kitchen convenience, cleaning, organization, time-saving, premium-looking household essentials. Exclude fashion, jewelry, supplements, medical products and risky items.
Use live web search to look for Japanese Rakuten ranking/bestsellers and Amazon Japan bestsellers, recent authentic customer reviews, and optionally public Threads purchase-intent posts. Do not assume inaccessible Threads data. Rank primarily by demonstrated purchase demand, review strength, target fit, and likely affiliate economics. Virality is secondary.
Only report information you can substantiate with direct public URLs. NEVER fabricate sales volume, review counts, ratings, affiliate commission rates, availability, prices, or affiliate URLs. Do not claim Amazon/Rakuten affiliate eligibility without evidence. Avoid products already featured if discoverable at https://nonkey826.github.io/kurashi-benricho-links/ . If uncertain, mark unknown.
Return ONLY valid JSON with the exact shape:
{{"products":[{{"name":"Japanese product name","category":"category","why_likely_to_sell":"evidence-based Japanese rationale","target_fit":"Japanese","estimated_price_jpy":null,"rakuten_url":null,"amazon_url":null,"evidence_urls":["https://..."],"sales_evidence":"Japanese; distinguish rankings from sales figures","reviews_evidence":"Japanese or unknown","threads_evidence":"Japanese or not verified","affiliate_rate":"unverified","risks":"Japanese","score":0}}]}}
Return at most 3 verified candidates. If insufficient evidence, return fewer or zero. score is integer 0-100 based on evidence quality and demand. All evidence_urls must be real links you visited in search, not guessed. Return only the JSON object, no markdown."""
payload = {"model":"gpt-4.1-mini","tools":[{"type":"web_search_preview"}],"input":prompt,"max_output_tokens":2400}
request = urllib.request.Request("https://api.openai.com/v1/responses",data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+os.environ["OPENAI_API_KEY"],"Content-Type":"application/json"},method="POST")
try:
    with urllib.request.urlopen(request,timeout=180) as resp:
        response=json.load(resp)
except urllib.error.HTTPError as exc:
    print("OpenAI API HTTP error:",exc.code,exc.read().decode()[:1000],file=sys.stderr)
    sys.exit(1)
texts=[]
for item in response.get("output",[]):
    if item.get("type")=="message":
        for part in item.get("content",[]):
            if part.get("type")=="output_text":
                texts.append(part.get("text",""))
raw="\n".join(texts).strip()
if raw.startswith("```"):
    raw=re.sub(r"^\x60{3}(?:json)?\s*|\s*\x60{3}$","",raw).strip()
try:
    result=json.loads(raw)
except ValueError:
    print("AI did not return valid JSON; preserving previous research.",file=sys.stderr)
    sys.exit(1)
products=result.get("products")
if not isinstance(products,list):
    sys.exit("Invalid product list")
clean=[]
for p in products[:3]:
    if not isinstance(p,dict) or not p.get("name") or not isinstance(p.get("evidence_urls"),list):
        continue
    urls=[u for u in p["evidence_urls"] if isinstance(u,str) and u.startswith("https://")]
    if not urls:
        continue
    p["evidence_urls"]=urls
    clean.append(p)
output={"schema_version":1,"brand":"暮らしの便利帖｜大人の愛用品","updated_at":dt.datetime.now(dt.timezone.utc).isoformat(),"status":"researched" if clean else "no_verified_candidates","research_policy":"sales_potential_first","products":clean}
OUTPUT.parent.mkdir(parents=True,exist_ok=True)
OUTPUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(f"Saved {len(clean)} researched candidates.")
