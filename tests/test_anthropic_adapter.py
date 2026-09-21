"""Tests fuer die Uebersetzung unserer Typen ins Anthropic-Format.

Hier wird nichts ans Netz geschickt: geprueft wird nur die reine
Umwandlung von Nachrichten - der Teil, der bei jedem neuen Anbieter
(Etappe 3) erneut richtig sein muss.
"""

from __future__ import annotations

from jarvis.models.anthropic_model import AnthropicModel
from jarvis.models.base import (
    AssistantMessage,
    ModelReply,
    ToolOutcome,
    ToolResultsMessage,
    Usage,
    UserMessage,
)


def test_nutzernachricht() -> None:
    api = AnthropicModel._to_api_messages([UserMessage(text="Hallo")])
    assert api == [{"role": "user", "content": "Hallo"}]


def test_assistentenantwort_wird_unveraendert_zurueckgegeben() -> None:
    """Die Originalbloecke muessen 1:1 zurueck, sonst verliert das Modell den Faden."""
    rohbloecke = [{"type": "text", "text": "hi"}]
    reply = ModelReply(text="hi", raw=rohbloecke)
    api = AnthropicModel._to_api_messages([AssistantMessage(reply=reply)])
    assert api == [{"role": "assistant", "content": rohbloecke}]


def test_werkzeugergebnisse_gehen_gesammelt_in_eine_nachricht() -> None:
    """Alle tool_results einer Runde gehoeren in EINE Nachricht."""
    nachricht = ToolResultsMessage(
        outcomes=(
            ToolOutcome(call_id="a", content="alles gut"),
            ToolOutcome(call_id="b", content="FEHLER: weg", is_error=True),
        )
    )
    api = AnthropicModel._to_api_messages([nachricht])
    assert len(api) == 1
    assert api[0]["role"] == "user"
    bloecke = api[0]["content"]
    assert [b["tool_use_id"] for b in bloecke] == ["a", "b"]
    assert bloecke[0]["is_error"] is False
    assert bloecke[1]["is_error"] is True


def test_ganzes_gespraech_in_richtiger_reihenfolge() -> None:
    verlauf = [
        UserMessage(text="Was steht in a.txt?"),
        AssistantMessage(reply=ModelReply(text="", raw=[{"type": "tool_use"}])),
        ToolResultsMessage(outcomes=(ToolOutcome(call_id="t1", content="Inhalt"),)),
    ]
    api = AnthropicModel._to_api_messages(verlauf)
    assert [m["role"] for m in api] == ["user", "assistant", "user"]


def test_usage_addiert_sich() -> None:
    gesamt = Usage(10, 5) + Usage(3, 2)
    assert (gesamt.input_tokens, gesamt.output_tokens, gesamt.total) == (13, 7, 20)
