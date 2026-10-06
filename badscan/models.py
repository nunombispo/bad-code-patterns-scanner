"""Shared scan types."""

import re
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

Severity = Literal["low", "medium", "high"]

SEVERITY_RANK: dict[str, int] = {"low": 0, "medium": 1, "high": 2}


class RegexDetect(BaseModel):
    """A textual pattern."""

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


class AstDetect(BaseModel):
    """A structural check chosen from the fixed AST catalog."""

    type: Literal["ast"]
    predicate: str
    exclude: list[str] = Field(default_factory=list)


Detect = Annotated[RegexDetect | AstDetect, Field(discriminator="type")]


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
    detect: Detect
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


class LearnFinding(BaseModel):
    """One observation from the learn agent, tied to a proposed pattern when it has one."""

    path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    observation: str
    proposed_pattern_id: str | None = None


class LearnResult(BaseModel):
    """Structured output of the learn agent. The schema stays fixed across models."""

    findings: list[LearnFinding] = Field(default_factory=list)
    patterns: list[Pattern] = Field(default_factory=list)


class ScannedFile(BaseModel):
    """One text file the engine can match against."""

    relative_path: str
    language: str
    text: str
    kind: Literal["source", "test", "config", "docs"] = "source"
