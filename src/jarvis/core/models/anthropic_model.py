"""Adapter fuer die Anthropic-API (Claude).

Wir schreiben die Werkzeugschleife selbst (statt den Tool-Runner des SDK zu
benutzen), weil der Agent spaeter mehrere Anbieter bedienen und vor JEDEM
Werkzeugaufruf das Approval-Gate aus Etappe 2 durchlaufen soll. Diese
Kontrolle ist hier wichtiger als ein paar gesparte Zeilen.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

import anthropic
from anthropic.types import MessageParam, ToolParam

from ...errors import ModelError
from .base import (
    AssistantMessage,
    Message,
    ModelReply,
    ToolCall,
    ToolResultsMessage,
    Usage,
    UserMessage,
)


class AnthropicModel:
    """Spricht mit Claude ueber das offizielle `anthropic`-SDK."""

    provider = "anthropic"

    def __init__(
        self,
        *,
        api_key: str,
        model_id: str = "claude-opus-5",
        max_tokens: int = 16000,
        timeout: float = 120.0,
    ) -> None:
        self.model_id = model_id
        self.max_tokens = max_tokens
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout)

    # -- Uebersetzung unserer Typen ins Anthropic-Format ------------------

    @staticmethod
    def _to_api_messages(messages: Sequence[Message]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for message in messages:
            match message:
                case UserMessage(text=text):
                    out.append({"role": "user", "content": text})
                case AssistantMessage(reply=reply):
                    # Originalbloecke unveraendert zurueckgeben.
                    out.append({"role": "assistant", "content": reply.raw})
                case ToolResultsMessage(outcomes=outcomes):
                    out.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": o.call_id,
                                    "content": o.content,
                                    "is_error": o.is_error,
                                }
                                for o in outcomes
                            ],
                        }
                    )
                case _:  # pragma: no cover - schuetzt vor Tippfehlern
                    raise ModelError(f"Unbekannter Nachrichtentyp: {type(message).__name__}")
        return out

    # -- Der eigentliche Aufruf -------------------------------------------

    def complete(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[dict[str, Any]],
    ) -> ModelReply:
        try:
            response = self._client.messages.create(
                model=self.model_id,
                max_tokens=self.max_tokens,
                system=system,
                tools=cast(list[ToolParam], list(tools)),
                messages=cast(list[MessageParam], self._to_api_messages(messages)),
            )
        except anthropic.AuthenticationError as exc:
            raise ModelError(
                "Die API hat den Schluessel abgelehnt. Stimmt ANTHROPIC_API_KEY in der .env?"
            ) from exc
        except anthropic.NotFoundError as exc:
            raise ModelError(
                f"Modell {self.model_id!r} gibt es nicht (oder nicht fuer deinen Zugang). "
                "Pruefe JARVIS_MODEL in der .env."
            ) from exc
        except anthropic.RateLimitError as exc:
            raise ModelError("Zu viele Anfragen (Rate Limit). Warte kurz und versuch es erneut.") from exc
        except anthropic.APIStatusError as exc:
            raise ModelError(f"Die API meldet einen Fehler ({exc.status_code}): {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            raise ModelError("Keine Verbindung zur API. Ist das Internet erreichbar?") from exc

        # Ablehnung durch die Sicherheitsfilter: kommt als normale Antwort mit
        # stop_reason "refusal" - also VOR dem Auslesen des Inhalts pruefen.
        if response.stop_reason == "refusal":
            raise ModelError("Das Modell hat die Anfrage abgelehnt (Sicherheitsfilter).")

        text_parts: list[str] = []
        calls: list[ToolCall] = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        # input ist bereits geparstes JSON - nie selbst am Text herumschneiden.
                        arguments=dict(block.input) if isinstance(block.input, dict) else {},
                    )
                )

        usage = response.usage
        return ModelReply(
            text="\n".join(p for p in text_parts if p).strip(),
            tool_calls=tuple(calls),
            usage=Usage(
                input_tokens=usage.input_tokens or 0,
                output_tokens=usage.output_tokens or 0,
                cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
                cache_write_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
            ),
            stop_reason=response.stop_reason,
            raw=response.content,
        )
