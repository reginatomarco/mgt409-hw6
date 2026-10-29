# Problem 4: With and Without a Cached Handbook

I ran all 12 practice documents twice on `gpt-6-luna`, once for each setup: 24 runs and 48 model calls in total. Every call is saved in `output/cache_test.json`. The script is `cache_test.py`, and costs are calculated from the token counts the API reported, priced with `data/prices.json`.

**Accuracy: 24 of 24 decisions matched `practice_key.json`.** Both setups made the same decisions on every document, and no trap tool was called.

> **Note on the data:** these numbers come from the run on 2026-10-28 at 23:26 UTC, which used the final agent with all three Problem 6 defenses on. The first Problem 4 run (23:06 UTC, before the defenses existed) was overwritten by mistake. Its results were nearly identical: $0.0272 vs. $0.0187, 31.3% saved, and the same cache behavior. The longer Problem 6 prompt adds about 250 tokens per call, which raises both setups by about 3%.

## Setups

| Setup | PydanticAI settings | Effect |
|---|---|---|
| `no_cache` | `openai_prompt_cache_options={"mode": "explicit"}` with no breakpoints | Nothing is cached, so every call pays the full input price for the handbook. |
| `cached` | explicit mode, `openai_cache_instructions=True`, one shared `openai_prompt_cache_key` | One cache breakpoint after the static instructions (prompt plus handbook), so that prefix is written to the cache and then read back. |

Each document takes 2 calls. Call 1 reads the system prompt and calls `read_document`. Call 2 receives the document text and returns the facts and decision. **The system prompt with the handbook is sent on both calls.**

## 1. Results

| | `no_cache` | `cached` |
|---|---|---|
| Model calls | 24 | 24 |
| Input tokens | 271,823 | 271,823 |
| of which cached reads | 0 | 133,428 |
| of which cache writes | 0 | 133,428 |
| of which full price | 271,823 | 4,967 |
| Output tokens | 1,378 | 1,377 |
| **Total cost (12 docs)** | **$0.027871** | **$0.019198** |
| **Cost per doc** | **$0.002323** | **$0.001600** |
| **Saved** | | **$0.008673 (31.1%)** |

Typical calls for one document:

| Call | `no_cache` | `cached` |
|---|---|---|
| 1 (read doc) | 11,259 tokens at full price = **$0.001132** | 11,119 tokens written to cache + 140 at full price = **$0.001410** |
| 2 (decide) | about 11,390 tokens at full price = **$0.00119** | 11,119 tokens read from cache + about 275 at full price = **$0.00019** |

## 2. Real numbers vs. the Problem 2 estimate

| | Problem 2 estimate | Real |
|---|---|---|
| Tokens of fixed prompt per call | 10,058 (handbook only, `tiktoken`) | **11,119** cached prefix, and 11,259 input tokens on call 1 |
| Calls per document | 1 (assumed) | **2** |
| Cost per 1,000 docs, no cache | $1.01 | **$2.32** |
| Cost per 1,000 docs, cached | $0.10 | **$1.60** |
| Savings | 90% | **31%** |

The difference has three causes:

1. **The prompt is bigger than the handbook.** It also includes the instructions and safety rules in `prompt.md`, the 3 tool definitions, the output schema, and message formatting. That adds about 1,200 tokens (11,259 vs. 10,058), about 12% more. The `tiktoken` count of the handbook itself was accurate: the full system prompt counts 10,906 locally.
2. **Every document takes 2 calls, and both carry the handbook.** That alone doubles the no-cache cost from about $1.0 to $2.32 per 1,000 docs.
3. **The cache never carried over from one document to the next (see section 4).** Problem 2 assumed 1 cache write and then 999 reads. In practice, every document paid a fresh write ($0.00139) and got only one read.

## 3. Projection: 1,000 docs a day for 30 days (30,000 docs)

| Scenario | Per doc | Per day (1,000 docs) | 30 days |
|---|---|---|---|
| No cache (measured) | $0.002323 | $2.32 | **$69.68** |
| Cached, as measured (a new write for every doc) | $0.001600 | $1.60 | **$47.99** (31% less) |
| Cached, if the cache carried over between docs* | $0.000321 | $0.32 | **$9.63** (86% less) |

\* This is a what-if built from the real per-call token counts: every call reads the 11,119-token prefix from the cache, and the one-time cache writes are left out because they are negligible at this volume. It's what the cache *should* deliver, and it's close to Problem 2's 90% estimate.

The token counts barely change from one document to the next (call 1 is identical every time, and call 2 ranges only from 11,374 to 11,419 input tokens). That makes these projections reliable as long as the document mix stays similar.

## 4. Surprises

1. **The cache never worked across documents, only within one.** Call 1 is exactly the same request for every document, and p02's call 1 was sent just 2 seconds after p01's. Even so, all 12 runs reported `cached_input_tokens = 0` and a fresh 11,119-token cache write on call 1. Only call 2, inside the same run, read from the cache. The same thing happened in the first Problem 4 run and in Problem 3 with the default (implicit) caching. My best guess is that Portkey or the provider sends each new run to a different backend server, each with its own cache. I didn't spend more on testing this. Fixing it is the difference between saving 31% and saving 86%.
2. **A cache write costs more than not caching.** It's $0.125 per 1M tokens vs. $0.10 at the normal input price, so call 1 in the cached setup cost 25% more than in `no_cache` ($0.001410 vs. $0.001132). Caching only pays off if the prefix gets read at least once. Here it got exactly one read per write, so the savings were modest.
3. **Half the cost is the "read the document" step.** Call 1 sends 11,259 tokens of input to get back a 13-token tool call. That's 49% of the no-cache cost, and 88% of the cached cost because of the write. Putting the document in the first message instead would make it 1 call per doc and roughly halve the cost. That is a design change and isn't done here; the assignment asks for a tool.
4. **Output tokens barely matter.** Even at 5 times the input price, output is only about 2.5% of the cost. The handbook is almost the whole bill.
5. **Caching didn't change the answers.** Decisions were identical across both setups, and output length was the same (1,378 vs. 1,377 tokens).
6. **Token counts were perfectly predictable.** Call 1 was 11,259 input tokens for all 24 runs, and the cached prefix was exactly 11,119 every time.

**Spent on this test:** $0.0471 for the run shown here, plus $0.0459 for the overwritten first run.
