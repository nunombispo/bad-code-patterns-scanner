"""Shared scan types.

Phase 1 stores findings and regex patterns. LearnResult arrives with the phase 2 agent.
"""

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Severity = Literal["low", "medium", "high"]

SEVERITY_RANK: dict[str, int] = {"low": 0, "medium": 1, "high": 2}


class RegexDetect(BaseModel):
    """A textual pattern. Phase 1 runs this detect type only."""

    type: Literal["regex"]
    regex: str
    exclude: list[str] = Field(default_factory=list)

    @field_validator("regex")
    @classmethod
    def regex_must_compile(cls, value: str) -> str:
        try:
            re.compile(value)
        except re.error as exc:
            raise ValueError(f"invalid regex: {exc}") from exc
        return value


class PatternExamples(BaseModel):
    match: str
    reject: str | None = None


class PatternOrigin(BaseModel):
    model: str | None = None
    repo: str | None = None
    confirmed_at: date | None = None


class Pattern(BaseModel):
    """One saved rule. The engine runs it without calling a model."""

    id: str = Field(pattern=r"^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)+$")
    status: Literal["confirmed", "candidate", "rejected"] = "confirmed"
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    category: str
    languages: list[str] = Field(default_factory=lambda: ["*"])
    message: str
    detect: RegexDetect
    examples: PatternExamples | None = None
    origin: PatternOrigin | None = None


class Finding(BaseModel):
    rule_id: str
    category: str
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    snippet: str
    message: str


class ScanResult(BaseModel):
    target: str
    files_scanned: int = Field(ge=0)
    findings: list[Finding]


class ScannedFile(BaseModel):
    """One text file the engine can match against."""

    relative_path: str
    language: str
    text: str
    kind: Literal["source", "test", "config", "docs"] = "source"
