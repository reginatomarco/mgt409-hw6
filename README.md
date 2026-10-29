# MGT 409 HW6: Campus Customs Vendor Desk Agent

A PydanticAI agent reads one vendor document (HTML, PDF or email), pulls out the vendor, SKU, unit price, lead time and minimum order, and decides **recommend** or **do_not_recommend** using the rules in `data/shop_handbook.md`. It uses only **gpt-6-luna** through Portkey.

**Start here:** open `output/hw6_report.html` by double-clicking it. It summarizes every result and works offline.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # then paste your PORTKEY_API_KEY into .env
```

Run every command from the `hw6/` folder.

## Run the agent

```bash
# One document, all three defenses on. Paid: about $0.0016 per document.
python agent.py --doc data/practice_docs/p01_bluehen_quote.html

# The same document with no defenses (the Problem 5/7 baseline)
python agent.py --doc data/practice_docs/p01_bluehen_quote.html --naive

# Only some defense layers (any mix of code, design, prompt)
python agent.py --doc data/exam_docs/e02_quote.html --defenses code,prompt

# Free dry run: no API call, no key needed, nothing logged
python agent.py --doc data/practice_docs/p01_bluehen_quote.html --offline
```

It prints the decision as JSON plus the tokens and dollars used. Every paid run adds an entry to:
- `output/usage_log.json`: tokens and cost
- `output/audit_trail.json`: tool calls, what the code layer removed, any rule overrides, and the final answer
- `output/trap_calls.json`: only if the agent tries `send_email` or `approve_payment` (it's an empty list now)

Other options: `--cache no_cache` turns off prompt caching, which is used for the Problem 4 comparison.

## Batch scripts (paid, about $0.02 per 12 docs)

| Command | What it does | Writes |
|---|---|---|
| `python cache_test.py` | 12 practice docs with and without a cached handbook | `output/cache_test.json` |
| `python attack_test.py --naive` | 12 practice docs, no defenses | `output/attack_results.json` |
| `python attack_test.py --out defense_results.json` | 12 practice docs, all defenses | `output/defense_results.json` |
| `python attack_test.py --defenses code --out layer_code_only.json` | One layer on its own | `output/layer_*_only.json` |

## Files

| File | What it is |
|---|---|
| `agent.py` | The agent: Portkey/gpt-6-luna setup, cost limits, cache settings, defense switches, logging, command line |
| `tools.py` | `read_document` (the code-layer cleaning) and the trap tools `send_email` and `approve_payment` |
| `models.py` | `VendorDecision` (the output) and `DeskDeps` (which document, which defenses) |
| `rules.py` | Design layer: checks each number against the document and applies the handbook's four checks in Python |
| `prompts/prompt.md` | The agent's instructions and its 8 safety rules. The handbook is added at the end on every call |
| `data/` | Handbook, prices, practice key, 12 practice docs, 10 exam docs, and my 2 attack docs (`my_attacks/`, with `my_attacks_key.json`) |
| `output/` | Every result and write-up. See the table below |
| `AI_prompts.md` | Every prompt I gave the AI, with a timestamp and problem number |

| Problem | Output |
|---|---|
| 2 · Handbook size | `handbook_estimate.md` |
| 3 · Agent | `harness.md` (fields, tools, logs, safety) |
| 4 · Caching | `cache_test.json`, `cache_test.md` |
| 5 · Attack (no defenses) | `attack_results.json`, `attack_results.md` |
| 6 · Defenses | `defense_results.json`, `defense_results.md`, `layer_*_only.json`, `attack_results_defended.json` |
| 7 · Red team | `red_team.md` |
| 8 · Exam | `exam_results.json` |
| 9 · Report | `hw6_report.html` |

## Safety notes

- The agent never really sends email or pays anyone. `send_email` and `approve_payment` are trap tools: they only write to `output/trap_calls.json`. With defenses on, they also need a human sign-off and are denied.
- Only `gpt-6-luna` is used, and the model name is hardcoded in `agent.py`.
- Each run is capped at 4 requests and 50,000 tokens, failed calls are not retried, and each request returns at most 300 output tokens.
- The real `.env` is ignored by git. Only `.env.example`, with a placeholder, is committed.
