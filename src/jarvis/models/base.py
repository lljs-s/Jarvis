"""Die einheitliche Sprache, die alle Modelle sprechen muessen.

Der Agent kennt NUR diese Typen. Er weiss nicht, ob dahinter Anthropic,
OpenAI oder ein lokales Ollama-Modell steckt. Genau deshalb ist Etappe 3
spaeter nur "eine weitere Datei in diesem Ordner".
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class Usage:
    """Verbrauchte Tokens einer Anfrage - Grundlage des Kostenzaehlers (Etappe 2)."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_read_tokens=self.cache_read_tokens + other.cache_read_tokens,
            cache_write_tokens=self.cache_write_tokens + other.cache_write_tokens,
        )

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class ToolCall:
    """Das Modell moechte ein Werkzeug benutzen."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolOutcome:
    """Unsere Antwort auf einen ToolCall."""

    call_id: str
    content: str
    is_error: bool = False


@dataclass(frozen=True)
class ModelReply:
    """Was ein Modell geantwortet hat."""

    text: str
    tool_calls: tuple[ToolCall, ...] = ()
    usage: Usage = field(default_factory=Usage)
    stop_reason: str | None = None
    # Originalantwort des Anbieters. Der Adapter schickt sie unveraendert
    # zurueck, wenn das Gespraech weitergeht (wichtig z. B. fuer Denkbloecke).
    raw: Any = None

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)


# --- Nachrichten im Gespraech ------------------------------------------------


@dataclass(frozen=True)
class UserMessage:
    text: str


@dataclass(frozen=True)
class AssistantMessage:
    reply: ModelReply


@dataclass(frozen=True)
class ToolResultsMessage:
    outcomes: tuple[ToolOutcome, ...]


Message = UserMessage | AssistantMessage | ToolResultsMessage


class ModelAdapter(Protocol):
    """Was jedes Modell koennen muss. Mehr verlangt der Agent nicht."""

    provider: str
    model_id: str

    def complete(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[dict[str, Any]],
    ) -> ModelReply:
        """Schickt das Gespraech ans Modell und liefert dessen Antwort."""
        ...
