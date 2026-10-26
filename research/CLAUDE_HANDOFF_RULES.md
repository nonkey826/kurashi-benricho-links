# Claude product candidate handoff — safety contract

Brand: 暮らしの便利帖｜大人の愛用品 only.

## Input and output
- Rakuten API raw source: `research/rakuten-candidates.json` (generated in manual test; not a posting ledger).
- AI review file: `research/claude-product-candidates.json` (currently generated as a temporary Actions artifact; not yet published in this repository).
- Existing `research/threads-products.json` remains untouched.

## Approval gate
Claude MUST NOT use a product for posting unless `approved_for_posting` is explicitly `true` AND product title, canonical merchant URL, affiliate URL, price and shop identity have each been independently verified for the same product. Missing fields or ambiguous identity mean reject. AI score alone never authorizes a post.

- `verification_status: api_data_only_merchant_identity_and_affiliate_not_verified` means **not approved**.
- Never treat affiliate redirects as independently verified merchant pages.
- Never invent products, URLs, sales, review counts, commission rates, or prices.
- Never substitute an Amazon link for a Rakuten listing.
- Keep product names and URLs paired using the original API item code and merchant identity.
- Do not change existing product ledgers, scheduled posts, or publishing automations from this file.
- If zero products pass, return zero and do not post a substitute.

## Current status (2026-10-27)
Rakuten API collection and OpenAI review have passed a manual workflow test. Eight scored candidates were produced as a short-lived artifact. Merchant identity verification and Claude scheduled-task integration are **not complete**. No automatic research schedule has been enabled.
