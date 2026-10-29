"""Output and dependency types for the vendor desk agent."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

DEFENSE_LAYERS = ("code", "design", "prompt")


@dataclass
class DeskDeps:
    """The one document this run is allowed to read (set by the person running the agent, not the model)."""

    doc_path: Path
    defenses: list[str] = field(default_factory=lambda: list(DEFENSE_LAYERS))  # [] = no defenses (Problem 5/7 baseline)
    cleaning: dict | None = None  # filled by read_document: what the code defense removed

    @property
    def code_defense(self) -> bool:
        return "code" in self.defenses


class VendorDecision(BaseModel):
    """What the vendor desk reports for one vendor document (handbook section 13)."""

    vendor: str = Field(description="Vendor name as the document states it.")
    sku: str | None = Field(description="Campus Customs SKU, e.g. CC-HD-006. null if the document does not say.")
    unit_price: float | None = Field(description="Quoted unit price in USD. null if the document does not say.")
    lead_time_days: int | None = Field(description="Quoted lead time in days. null if the document does not say.")
    min_order: int | None = Field(description="Minimum order in units. null if the document does not say.")
    decision: Literal["recommend", "do_not_recommend"]
    reason: str = Field(description="One sentence naming the purchasing check that decided it.")
