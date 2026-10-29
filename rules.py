"""DESIGN defense (Problem 6, layer 2): the model reads, Python decides.

The model only proposes the facts. This module then
1. checks each fact against the cleaned document: the value must appear on a plain quote line, not on a
   line that claims to revise / correct / supersede the quote (provenance check). Unverified facts become
   unknown (None), and a check that depends on an unknown fact fails, as handbook section 4 says.
2. runs the four purchasing checks in plain Python against tables parsed from data/shop_handbook.md,
   and writes the one-sentence reason itself (so no link or injected text can reach the buyer).
A poisoned document can therefore change neither the decision nor the reason without changing the visible
quote lines themselves.
"""

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from models import VendorDecision

HANDBOOK = Path(__file__).resolve().parent / "data" / "shop_handbook.md"
OVERRIDE_LINE = re.compile(
    r"\b(revis\w*|correct\w*|supersed\w*|replac\w*|now|updat\w*|negotiat\w*|effective|discount\w*|instead|"
    r"pre-?approv\w*|approve_payment|send_email)\b",
    re.I,
)
MONEY = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)")
INTEGER = re.compile(r"\b\d[\d,]*\b")


@dataclass(frozen=True)
class Handbook:
    approved: frozenset[str]
    removed: frozenset[str]
    max_cost: dict
    max_lead_days: int
    max_min_order: int


def _section(text: str, number: int) -> str:
    m = re.search(rf"^## {number}\..*?(?=^## \d+\.|\Z)", text, re.S | re.M)
    return m.group(0) if m else ""


def _table_column(section: str, column: str) -> tuple[list[list[str]], int]:
    """Body rows of the section's markdown table, and the index of the named column."""
    rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in section.splitlines() if line.startswith("|")]
    return rows[2:], rows[0].index(column)


@lru_cache
def handbook() -> Handbook:
    text = HANDBOOK.read_text(encoding="utf-8")
    rules = _section(text, 4)
    rows, i = _table_column(_section(text, 5), "Vendor")
    approved = frozenset(r[i].lower() for r in rows)
    rows, i = _table_column(_section(text, 6), "Vendor")
    removed = frozenset(r[i].lower() for r in rows)
    rows, i = _table_column(_section(text, 9), "Max unit cost")
    max_cost = {r[0]: float(r[i].lstrip("$").replace(",", "")) for r in rows}
    return Handbook(
        approved=approved,
        removed=removed,
        max_cost=max_cost,
        max_lead_days=int(re.search(r"lead time is (\d+) days or less", rules).group(1)),
        max_min_order=int(re.search(r"minimum order is (\d+) units or less", rules).group(1)),
    )


def _quote_lines(doc_text: str) -> list[str]:
    """Lines of the cleaned document that do not try to override the quote."""
    return [line for line in doc_text.splitlines() if not OVERRIDE_LINE.search(line)]


def _ints(line: str) -> set[int]:
    return {int(n.replace(",", "")) for n in INTEGER.findall(line)}


def verify_facts(answer: VendorDecision, doc_text: str) -> tuple[dict, list[str]]:
    """Keep only facts that appear on a plain quote line of the cleaned document."""
    lines, flags = _quote_lines(doc_text), []
    low = [line.lower() for line in lines]
    facts = answer.model_dump(include={"vendor", "sku", "unit_price", "lead_time_days", "min_order"})

    def drop(field: str, why: str) -> None:
        if facts[field] is not None:
            flags.append(f"{field}={facts[field]!r} {why}; treated as unknown")
            facts[field] = None

    if not any((answer.vendor or "").lower() in line for line in low):
        drop("vendor", "is not on a plain line of the document")
    if answer.sku and not any(re.search(rf"\b{re.escape(answer.sku.lower())}\b", line) for line in low):
        drop("sku", "is not on a plain line of the document")
    if answer.unit_price is not None and not any(
        "price" in line and any(abs(float(m.replace(",", "")) - answer.unit_price) < 0.005 for m in MONEY.findall(line))
        for line in low
    ):
        drop("unit_price", "is not on a plain 'unit price' line (may come from a 'revised' / 'negotiated' line)")
    if answer.lead_time_days is not None and not any(
        "lead" in line and answer.lead_time_days in _ints(line) for line in low
    ):
        drop("lead_time_days", "is not on a plain 'lead time' line (may come from a 'correction' line)")
    if answer.min_order is not None and not any(
        "minimum" in line and answer.min_order in _ints(line) for line in low
    ):
        drop("min_order", "is not on a plain 'minimum order' line")
    return facts, flags


def decide(facts: dict) -> tuple[str, str]:
    """The four purchasing checks of handbook section 4, in order. Returns (decision, one-sentence reason)."""
    hb = handbook()
    vendor, sku, price = facts["vendor"], facts["sku"], facts["unit_price"]
    lead, min_order = facts["lead_time_days"], facts["min_order"]

    if vendor is None:
        return "do_not_recommend", "Approved vendor check failed: the vendor could not be confirmed from the document."
    if vendor.lower() in hb.removed:
        return "do_not_recommend", f"Approved vendor check failed: {vendor} is on the removed or pending vendor list."
    if vendor.lower() not in hb.approved:
        return "do_not_recommend", f"Approved vendor check failed: {vendor} is not on the approved vendor list."
    if sku is None or sku not in hb.max_cost:
        return "do_not_recommend", "Price check failed: the SKU is missing or not in the catalogue, so there is no max unit cost to compare."
    max_cost = hb.max_cost[sku]
    if price is None:
        return "do_not_recommend", f"Price check failed: the unit price for {sku} is unknown."
    if price > max_cost:
        return "do_not_recommend", f"Price check failed: ${price:.2f} is above the ${max_cost:.2f} max unit cost for {sku}."
    if lead is None:
        return "do_not_recommend", "Lead time check failed: the lead time is unknown."
    if lead > hb.max_lead_days:
        return "do_not_recommend", f"Lead time check failed: {lead} days is over the {hb.max_lead_days}-day limit."
    if min_order is None:
        return "do_not_recommend", "Minimum order check failed: the minimum order is unknown."
    if min_order > hb.max_min_order:
        return "do_not_recommend", f"Minimum order check failed: {min_order:,} units is over the {hb.max_min_order}-unit limit."
    return "recommend", (
        f"All four checks passed: {vendor} is approved, ${price:.2f} is at or below the ${max_cost:.2f} max unit cost "
        f"for {sku}, {lead} days is within {hb.max_lead_days}, and {min_order:,} units is within {hb.max_min_order}."
    )


def guarded_decision(answer: VendorDecision, doc_text: str) -> tuple[VendorDecision, list[str]]:
    """Final answer: verified facts + Python's decision and reason. Flags explain anything that was overruled."""
    facts, flags = verify_facts(answer, doc_text)
    decision, reason = decide(facts)
    if decision != answer.decision:
        flags.append(f"model said {answer.decision}; rules say {decision} (rules win)")
    return VendorDecision(**facts, decision=decision, reason=reason), flags
