"""One Pydantic AI agent proposes patterns. The model is chosen per run."""

import os

from pydantic_ai import Agent
from pydantic_ai.models import Model

from badscan.engine.ast_catalog import PREDICATES
from badscan.learn.select import Chunk
from badscan.models import LearnResult

INSTRUCTIONS = (
    "Propose reusable bad-code patterns for generated code "
    "that was merged without review. Return findings and rules."
)

agent = Agent(output_type=LearnResult, instructions=INSTRUCTIONS)


def propose(prompt: str, model: str | Model) -> LearnResult:
    """Run the shared agent. Tests pass TestModel; operators pass BADSCAN_MODEL."""

    result = agent.run_sync(prompt, model=model)
    return result.output


def resolve_model(model: str | Model | None) -> str | Model:
    if model is not None:
        return model
    configured = os.environ.get("BADSCAN_MODEL")
    if not configured:
        raise ValueError("--learn requires BADSCAN_MODEL")
    return configured


def build_prompt(chunks: list[Chunk], known_ids: set[str]) -> str:
    lines = [
        "Known rule ids, do not propose these:",
        *sorted(known_ids),
        "",
        "AST predicates you may name: " + ", ".join(sorted(PREDICATES)),
        "Each pattern needs a match example and a reject example.",
        "Prefer an id that starts with learned.",
        "",
        "Source chunks:",
    ]
    if not known_ids:
        lines.insert(1, "(none)")
    for chunk in chunks:
        lines.append(f"--- {chunk.path}:{chunk.start_line}-{chunk.end_line} ({chunk.language})")
        lines.append(chunk.text)
    return "\n".join(lines)
