from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Literal, Optional

Action = Literal["insert_after", "insert_before", "strike_text", "replace_text", "no_change", "review"]
Decision = Literal["pending", "accepted", "rejected"]

@dataclass
class TranscriptSegment:
    id: str
    start: float
    end: float
    text: str
    category: str = "contenu"
    confidence: Optional[float] = None

@dataclass
class DocumentBlock:
    id: str
    index: int
    text: str
    style: str = ""
    starred: bool = False

@dataclass
class Suggestion:
    id: str
    action: Action
    block_id: str
    anchor_text: str
    new_text: str
    reason: str
    confidence: float
    evidence: str = ""
    timestamp_start: Optional[float] = None
    timestamp_end: Optional[float] = None
    category: str = "modification"
    auto_safe: bool = False
    decision: Decision = "pending"

    def to_dict(self):
        return asdict(self)
