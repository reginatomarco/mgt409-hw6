# Handbook Size and Cost Estimate

## 1. Token count

**`data/shop_handbook.md` = 10,058 tokens**

How I got it:

- I counted the tokens offline with OpenAI's `tiktoken` library (v0.14.0), using the `o200k_base` encoding. That is the tokenizer used by OpenAI's current GPT models, so it is the closest match for `gpt-6-luna`. This cost $0 because no API call was made.
- I checked the count two other ways:

| Method | Count |
|---|---|
| `o200k_base` (used) | **10,058** |
| `cl100k_base` (older GPT tokenizer) | 10,184 |
| Rule of thumb: 28,903 characters ÷ 4 | ~7,226 |

The rule of thumb comes in about 28% low. The handbook is heavy on tables, prices, and SKUs, and numbers and symbols split into more tokens than plain English does. The exact count from the provider could be off by a few tokens because of message formatting overhead.

```python
import tiktoken
text = open("data/shop_handbook.md", encoding="utf-8").read()
len(tiktoken.get_encoding("o200k_base").encode(text))   # -> 10058
```

## 2. Prices (`data/prices.json`, gpt-6-luna, per 1M tokens)

| Type | $ / 1M tokens | $ / token |
|---|---|---|
| Input (uncached) | $0.10 | $0.0000001 |
| Cache write | $0.125 | $0.000000125 |
| Cached input (read) | $0.01 | $0.00000001 |
| Output | $0.50 | not used here; the handbook is input only |

## 3. Cost of the handbook alone

### Without caching

Every call pays the full input price for all 10,058 tokens.

- **Per call:** 10,058 × $0.10 / 1,000,000 = **$0.0010058** (about $0.001, or 0.1¢)
- **1,000 calls:** 1,000 × $0.0010058 = **$1.0058** (about **$1.01**)

### With caching

The first call writes the handbook to the cache. Every call after that reads it from the cache.

- **First call (cache write):** 10,058 × $0.125 / 1,000,000 = **$0.00125725**
- **Each later call (cache read):** 10,058 × $0.01 / 1,000,000 = **$0.00010058** (about 0.01¢)
- **1,000 calls:** $0.00125725 + 999 × $0.00010058
  = $0.00125725 + $0.10047942
  = **$0.10173667** (about **$0.10**)

### Summary

| | Per call | 1,000 calls |
|---|---|---|
| No cache | $0.0010058 | **$1.0058** |
| Cached (1 write, then 999 reads) | $0.0001006 (read) / $0.0012573 (first) | **$0.1017** |
| **Savings** | | **$0.9041 (about 90% less)** |

**Assumptions:**

- The cache stays warm for all 1,000 calls, so there is only one cache write. If the cache expires between batches, each new batch pays the $0.00126 write again.
- Caching only matches the beginning of the prompt. The handbook must be sent first and must be identical on every call, with the vendor document after it.
