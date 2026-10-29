"""Problem 4: run all 12 practice docs with and without a cached handbook; log every model call.

    python cache_test.py   # PAID: 24 runs of gpt-6-luna (~48 calls, about $0.04)

Writes output/cache_test.json (one entry per model call). Each run is also logged to usage_log.json and
audit_trail.json by agent.review, like any other run.
"""

import json
import sys
from pathlib import Path

from pydantic_ai.messages import ModelResponse

from agent import CACHE_SETUPS, MODEL_NAME, review, run_cost
from tools import OUTPUT_DIR, utc_now

DOCS = sorted((Path(__file__).resolve().parent / "data" / "practice_docs").iterdir())
KEY = {e["file"]: e for e in json.loads((Path(__file__).resolve().parent / "data" / "practice_key.json").read_text())}


def call_record(setup: str, doc: Path, n: int, m: ModelResponse) -> dict:
    u = m.usage
    tokens = {
        "input_tokens": u.input_tokens,
        "cached_input_tokens": u.cache_read_tokens,
        "cache_write_tokens": u.cache_write_tokens,
        "uncached_input_tokens": u.input_tokens - u.cache_read_tokens - u.cache_write_tokens,
        "output_tokens": u.output_tokens,
    }
    return {
        "setup": setup,
        "document": doc.name,
        "call": n,
        "time": m.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "model": m.model_name,
        **tokens,
        "other_reported_counts": dict(u.details),  # e.g. reasoning_tokens, as the API reported them
        "cost_usd": round(run_cost(tokens), 8),
    }


def main() -> None:
    calls = []
    for setup in ["no_cache", "cached"]:
        for doc in DOCS:
            print(f"--- {setup} | {doc.name}")
            output, messages = review(doc, setup=setup)
            responses = [m for m in messages if isinstance(m, ModelResponse)]
            calls += [call_record(setup, doc, i + 1, m) for i, m in enumerate(responses)]
            if output is None and not calls:
                sys.exit("first run failed before any call was made: stopping so we don't spend more")
            want = KEY.get(doc.name, {}).get("decision")
            got = output.decision if output else None
            print(f"    decision {got} | key {want} | {'OK' if got == want else 'MISMATCH'}")
    (OUTPUT_DIR / "cache_test.json").write_text(
        json.dumps({"model": MODEL_NAME, "run_at": utc_now(), "setups": {k: dict(v) for k, v in CACHE_SETUPS.items()}, "calls": calls}, indent=2),
        encoding="utf-8",
    )
    print(f"\nwrote {len(calls)} calls to output/cache_test.json")


if __name__ == "__main__":
    main()
