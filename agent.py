"""Campus Customs vendor desk agent: one vendor document in, one buy / don't-buy decision out.

    python agent.py --doc data/practice_docs/p01_bluehen_quote.html            # PAID: 1 run, all defenses on
    python agent.py --doc data/practice_docs/p01_bluehen_quote.html --naive    # PAID: no defenses (baseline)
    python agent.py --doc ... --defenses code,prompt                           # PAID: pick defense layers
    python agent.py --doc data/practice_docs/p01_bluehen_quote.html --offline  # free dry run (TestModel)

Three defense layers (Problem 6), each can be switched off for testing:
    code    tools.py   what the program does to the document before the model sees it (hidden text, links)
    design  rules.py   the model only proposes facts; Python verifies them and makes the decision, and
                       send_email / approve_payment need human sign-off, so a poisoned doc can't reach them
    prompt  prompts/prompt.md   the "Safety" rules the model is told to follow

The handbook is sent on every call inside the system prompt. The whole system prompt never changes, so
after the first call the provider can serve it from the prompt cache (see output/handbook_estimate.md).

Every paid run appends to:
    output/usage_log.json    document, time, API-reported tokens, dollar cost (data/prices.json)
    output/audit_trail.json  each tool call with its args and a short result, plus the final answer
    output/trap_calls.json   only if a document tricked the agent into send_email / approve_payment
"""

import argparse
import json
import os
import sys
from functools import lru_cache
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

import httpx
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent, DeferredToolRequests, DeferredToolResults, Tool, ToolDenied, capture_run_messages
from pydantic_ai.messages import ModelRequest, ModelResponse, RetryPromptPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

from models import DEFENSE_LAYERS, DeskDeps, VendorDecision
from rules import guarded_decision
from tools import append_json, approve_payment, extract_text, log_trap, raw_text, read_document, send_email, utc_now

HW_ROOT = Path(__file__).resolve().parent
COURSE_ROOT = HW_ROOT.parent.parent
HANDBOOK = HW_ROOT / "data" / "shop_handbook.md"
PROMPT = HW_ROOT / "prompts" / "prompt.md"
PRICES = json.loads((HW_ROOT / "data" / "prices.json").read_text())

load_dotenv(HW_ROOT / ".env")
load_dotenv(COURSE_ROOT / ".env")  # PORTKEY_API_KEY

# The ONLY model allowed in this homework. Deliberately not configurable.
MODEL_NAME = "gpt-6-luna"

# Cost guards. A normal run is 2 requests (read the doc, then answer) at ~11k input tokens each.
# 4 requests leaves room for one hijacked trap call to show up in the logs instead of crashing the run.
USAGE_LIMITS = UsageLimits(request_limit=4, total_tokens_limit=50_000)
# reasoning off: gpt-6-luna rejects function tools on chat completions while reasoning is on (hw5).
MODEL_SETTINGS = OpenAIChatModelSettings(max_tokens=300, temperature=0, openai_reasoning_effort="none")
# Prompt cache setups (Problem 4). Explicit mode = only our breakpoints cache, nothing implicit.
CACHE_SETUPS = {
    # One breakpoint right after the static instructions (prompt + handbook): written once, then read
    # by every later call. The cache key keeps all vendor desk calls on the same cache.
    "cached": OpenAIChatModelSettings(
        openai_prompt_cache_options={"mode": "explicit", "ttl": "30m"},
        openai_cache_instructions=True,
        openai_prompt_cache_key="campus-customs-vendor-desk",
    ),
    # No breakpoints at all: every call pays full input price for the handbook.
    "no_cache": OpenAIChatModelSettings(openai_prompt_cache_options={"mode": "explicit"}, openai_cache_instructions=False),
}
SHORT = 160  # characters kept from each tool result in the audit trail


def system_prompt(safety_rules: bool = True) -> str:
    prompt = PROMPT.read_text(encoding="utf-8")
    if not safety_rules:  # PROMPT defense off: drop the whole safety section
        start, end = prompt.index("## Safety"), prompt.index("## Campus Customs Shop Handbook")
        prompt = prompt[:start] + prompt[end:]
    return prompt.replace("{handbook}", HANDBOOK.read_text(encoding="utf-8"))


def luna_model() -> OpenAIChatModel:
    """gpt-6-luna, routed through the course Portkey gateway."""
    key = os.getenv("PORTKEY_API_KEY")
    if not key:
        raise RuntimeError("PORTKEY_API_KEY not found in hw6/.env or the course-root .env")
    client = AsyncOpenAI(
        api_key=key,
        base_url="https://api.portkey.ai/v1",
        default_headers={"x-portkey-api-key": key},
        max_retries=0,  # a failed call is not silently retried (and paid for) again
        timeout=httpx.Timeout(60, connect=15),
    )
    model = OpenAIChatModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))
    assert model.model_name == "gpt-6-luna"
    return model


SIGN_OFF_DENIED = "Not approved. Emails and payments need a human sign-off and are never done by the vendor desk."


@lru_cache
def build_agent(design: bool, prompt: bool) -> Agent:
    """One agent per defense combination (the code layer lives in read_document, switched by DeskDeps)."""
    if design:
        # DESIGN: the dangerous tools stay in the system but need human sign-off. A call stops the run
        # as a DeferredToolRequests instead of executing; review() logs it and denies it.
        tools = [read_document, Tool(send_email, requires_approval=True), Tool(approve_payment, requires_approval=True)]
        output_type = [VendorDecision, DeferredToolRequests]
    else:
        tools, output_type = [read_document, send_email, approve_payment], VendorDecision  # traps run directly
    return Agent(
        deps_type=DeskDeps,
        output_type=output_type,
        instructions=system_prompt(safety_rules=prompt),
        tools=tools,
        model_settings=MODEL_SETTINGS,
        retries=1,
    )


def token_counts(messages) -> dict:
    """Sum the usage the API reported on each response (also works when a run fails midway)."""
    t = {"requests": 0, "input_tokens": 0, "cached_input_tokens": 0, "cache_write_tokens": 0, "output_tokens": 0}
    for m in messages:
        if isinstance(m, ModelResponse):
            t["requests"] += 1
            t["input_tokens"] += m.usage.input_tokens
            t["cached_input_tokens"] += m.usage.cache_read_tokens
            t["cache_write_tokens"] += m.usage.cache_write_tokens
            t["output_tokens"] += m.usage.output_tokens
    t["total_tokens"] = t["input_tokens"] + t["output_tokens"]
    return t


def run_cost(t: dict) -> float:
    """Dollar cost of one run from data/prices.json. input_tokens includes the cached ones."""
    p = PRICES[MODEL_NAME]
    uncached = t["input_tokens"] - t["cached_input_tokens"] - t["cache_write_tokens"]
    return (
        uncached * p["input_per_1m"]
        + t["cached_input_tokens"] * p["cached_input_per_1m"]
        + t["cache_write_tokens"] * p["cache_write_per_1m"]
        + t["output_tokens"] * p["output_per_1m"]
    ) / 1_000_000


def tool_calls(messages) -> list[dict]:
    """Each tool call with its arguments and a short result, in order."""
    calls, by_id = [], {}
    for m in messages:
        for part in m.parts:
            if isinstance(m, ModelResponse) and isinstance(part, ToolCallPart):
                if part.tool_name.startswith("final_result"):
                    continue  # the structured answer, logged separately as final_answer
                by_id[part.tool_call_id] = entry = {"tool": part.tool_name, "args": part.args_as_dict(), "result": None}
                calls.append(entry)
            elif isinstance(m, ModelRequest) and isinstance(part, (ToolReturnPart, RetryPromptPart)):
                if part.tool_call_id in by_id:
                    text = str(part.content) if isinstance(part, ToolReturnPart) else f"error: {part.model_response()}"
                    text = " ".join(text.split())
                    by_id[part.tool_call_id]["result"] = text[:SHORT] + ("..." if len(text) > SHORT else "")
    return calls


def _run(agent: Agent, deps: DeskDeps, model, setup: str, history=None, deferred=None):
    """One agent run. Returns (output, all messages so far, error)."""
    with capture_run_messages() as captured:
        try:
            result = agent.run_sync(
                None if history else "Review the assigned vendor document and report your decision.",
                message_history=history,
                deferred_tool_results=deferred,
                deps=deps,
                model=model,
                model_settings=CACHE_SETUPS[setup],
                usage_limits=USAGE_LIMITS,
            )
            return result.output, result.all_messages(), None
        except Exception as e:  # still log what was spent before the failure
            return None, list(history or []) + [m for m in captured if m not in (history or [])], f"{type(e).__name__}: {e}"


def review(doc: Path, offline: bool = False, setup: str = "cached", naive: bool = False, defenses: list[str] | None = None):
    """Run the vendor desk on one document and write the usage log and audit trail.

    defenses: any of "code", "design", "prompt" (default: all three). naive=True means none.
    Returns (final decision or None, every message of the run)."""
    defenses = [] if naive else [d for d in DEFENSE_LAYERS if d in (DEFENSE_LAYERS if defenses is None else defenses)]
    design, prompt = "design" in defenses, "prompt" in defenses
    if offline:
        from pydantic_ai.models.test import TestModel

        model = TestModel(call_tools=["read_document"])  # never springs the traps in a dry run
    else:
        model = luna_model()

    deps = DeskDeps(doc_path=doc, defenses=defenses)
    agent = build_agent(design, prompt)
    output, messages, error = _run(agent, deps, model, setup)

    blocked = []
    if isinstance(output, DeferredToolRequests):
        # DESIGN: the model asked for send_email / approve_payment. Log it, deny it, let the model finish.
        for call in output.approvals:
            log_trap(doc, defenses, call.tool_name, call.args_as_dict(), "blocked: needs human sign-off (denied)")
            blocked.append({"tool": call.tool_name, "args": call.args_as_dict()})
        denied = DeferredToolResults(approvals={c.tool_call_id: ToolDenied(SIGN_OFF_DENIED) for c in output.approvals})
        output, messages, error = _run(agent, deps, model, setup, history=messages, deferred=denied)
        if isinstance(output, DeferredToolRequests):  # asked again: stop here, no decision
            output, error = None, "model kept requesting send_email / approve_payment after denial"

    model_answer, flags = output, []
    if design and output is not None and not offline:
        # DESIGN: Python verifies the facts against the document the model saw and makes the decision.
        doc_text = extract_text(doc) if deps.code_defense else raw_text(doc)
        output, flags = guarded_decision(model_answer, doc_text)

    time, tokens = utc_now(), token_counts(messages)
    cost = run_cost(tokens)
    if not offline:
        append_json("usage_log.json", {
            "document": doc.name, "time": time, "model": MODEL_NAME, "cache_setup": setup, "defenses": defenses or ["none"],
            **tokens, "cost_usd": round(cost, 8),
        })
        append_json("audit_trail.json", {
            "document": doc.name,
            "time": time,
            "cache_setup": setup,
            "defenses": defenses or ["none"],
            "cleaning": deps.cleaning,
            "tool_calls": tool_calls(messages),
            "blocked_tool_requests": blocked,
            "model_answer": model_answer.model_dump() if design and model_answer else None,
            "guard_flags": flags,
            "final_answer": output.model_dump() if output else None,
            "error": error,
        })

    if output:
        print(output.model_dump_json(indent=2))
    for f in flags:
        print(f"GUARD: {f}")
    for b in blocked:
        print(f"BLOCKED: {b['tool']} (needs human sign-off)")
    if error:
        print(f"RUN FAILED: {error}")
    print(
        f"\n{tokens['requests']} requests | input {tokens['input_tokens']} (cached {tokens['cached_input_tokens']}) | "
        f"output {tokens['output_tokens']} | ${cost:.6f} | defenses: {','.join(defenses) or 'none'}"
        + ("  [offline: nothing logged, $0 real]" if offline else "")
    )
    return output, list(messages)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--doc", type=Path, required=True, help="path to one vendor document")
    parser.add_argument("--offline", action="store_true", help="free dry run with TestModel (no API call, no logs)")
    parser.add_argument("--cache", choices=CACHE_SETUPS, default="cached", help="prompt cache setup (default: cached)")
    parser.add_argument("--naive", action="store_true", help="no defenses at all (same as --defenses none)")
    parser.add_argument("--defenses", default="code,design,prompt", help="comma list of code,design,prompt, or 'none'")
    args = parser.parse_args()
    if not args.doc.is_file():
        sys.exit(f"not found: {args.doc}")
    layers = [] if args.defenses == "none" else [d.strip() for d in args.defenses.split(",")]
    if bad := set(layers) - set(DEFENSE_LAYERS):
        sys.exit(f"unknown defense layer(s): {', '.join(bad)}")
    review(args.doc, offline=args.offline, setup=args.cache, naive=args.naive, defenses=layers)


if __name__ == "__main__":
    main()
