"""Tests fuer die Agent-Schleife - komplett ohne API und ohne Kosten.

Statt des echten Modells steckt ein "FakeModel" im Agenten, das vorher
festgelegte Antworten liefert. So laesst sich die Schleife genau pruefen.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, ClassVar

import pytest

from jarvis.agent import Agent, AgentEvent
from jarvis.errors import ToolError
from jarvis.models.base import Message, ModelReply, ToolCall, Usage
from jarvis.tools.base import RiskLevel, Tool, ToolResult
from jarvis.tools.files import default_tools
from jarvis.tools.registry import ToolRegistry
from jarvis.workspace import Workspace


class FakeModel:
    """Ein Modell-Ersatz, der abgesprochene Antworten abspielt."""

    provider = "fake"
    model_id = "fake-1"

    def __init__(self, replies: list[ModelReply]) -> None:
        self.replies = replies
        self.calls: list[list[Message]] = []

    def complete(
        self, *, system: str, messages: Sequence[Message], tools: Sequence[dict[str, Any]]
    ) -> ModelReply:
        self.calls.append(list(messages))
        if not self.replies:
            return ModelReply(text="fertig", usage=Usage(1, 1))
        return self.replies.pop(0)


class GefaehrlichesWerkzeug(Tool):
    """Nur fuer den Test: haette Risikostufe HIGH."""

    name = "loesche_alles"
    description = "Test-Werkzeug mit hohem Risiko."
    risk = RiskLevel.HIGH
    input_schema: ClassVar[dict[str, Any]] = {"type": "object", "properties": {}, "required": []}
    ausgefuehrt = False

    def run(self, **kwargs: Any) -> ToolResult:  # pragma: no cover - darf nie laufen
        GefaehrlichesWerkzeug.ausgefuehrt = True
        return ToolResult("passiert nicht")


def _agent(workspace: Workspace, replies: list[ModelReply], **kwargs: Any) -> tuple[Agent, FakeModel]:
    model = FakeModel(replies)
    registry = ToolRegistry(default_tools(workspace))
    return Agent(model=model, tools=registry, **kwargs), model


def test_antwort_ohne_werkzeug(filled_workspace: Workspace) -> None:
    agent, _ = _agent(filled_workspace, [ModelReply(text="Hallo!", usage=Usage(10, 5))])
    result = agent.run("Sag Hallo")
    assert result.answer == "Hallo!"
    assert result.steps == 1
    assert result.tool_calls == 0
    assert result.usage.input_tokens == 10


def test_werkzeug_wird_ausgefuehrt_und_ergebnis_zurueckgegeben(filled_workspace: Workspace) -> None:
    replies = [
        ModelReply(
            text="Ich schaue nach.",
            tool_calls=(ToolCall(id="t1", name="read_file", arguments={"path": "brief.md"}),),
            usage=Usage(10, 5),
        ),
        ModelReply(text="In brief.md steht 'Hallo Welt'.", usage=Usage(20, 8)),
    ]
    agent, model = _agent(filled_workspace, replies)
    result = agent.run("Was steht in brief.md?")

    assert "Hallo Welt" in result.answer
    assert result.steps == 2
    assert result.tool_calls == 1
    # Tokens beider Runden werden addiert
    assert result.usage.input_tokens == 30
    # Das Modell hat beim zweiten Aufruf das Werkzeugergebnis gesehen
    letzte_nachrichten = model.calls[-1]
    assert any("Hallo Welt" in str(m) for m in letzte_nachrichten)


def test_mehrere_werkzeuge_in_einer_runde(filled_workspace: Workspace) -> None:
    replies = [
        ModelReply(
            text="",
            tool_calls=(
                ToolCall(id="t1", name="list_files", arguments={}),
                ToolCall(id="t2", name="read_file", arguments={"path": "brief.md"}),
            ),
        ),
        ModelReply(text="fertig"),
    ]
    agent, _ = _agent(filled_workspace, replies)
    result = agent.run("Schau dir alles an")
    assert result.tool_calls == 2


def test_hohes_risiko_wird_blockiert(filled_workspace: Workspace) -> None:
    """Etappe-1-Garantie: HIGH-Aktionen laufen NICHT ohne Bestaetigung."""
    registry = ToolRegistry(default_tools(filled_workspace))
    registry.add(GefaehrlichesWerkzeug())
    ereignisse: list[AgentEvent] = []
    model = FakeModel(
        [
            ModelReply(
                text="",
                tool_calls=(ToolCall(id="t1", name="loesche_alles", arguments={}),),
            ),
            ModelReply(text="Konnte ich nicht tun."),
        ]
    )
    agent = Agent(model=model, tools=registry, on_event=ereignisse.append)
    result = agent.run("Loesche alles")

    assert GefaehrlichesWerkzeug.ausgefuehrt is False
    assert any(e.kind == "blocked" for e in ereignisse)
    assert result.answer == "Konnte ich nicht tun."


def test_sandbox_verstoss_beendet_die_aufgabe_nicht(filled_workspace: Workspace) -> None:
    """Das Modell bekommt die Ablehnung als Fehlermeldung und darf es besser machen."""
    ereignisse: list[AgentEvent] = []
    replies = [
        ModelReply(
            text="",
            tool_calls=(ToolCall(id="t1", name="read_file", arguments={"path": "../../etc/passwd"}),),
        ),
        ModelReply(text="Darauf habe ich keinen Zugriff."),
    ]
    agent, _ = _agent(filled_workspace, replies, on_event=ereignisse.append)
    result = agent.run("Lies /etc/passwd")

    assert result.answer == "Darauf habe ich keinen Zugriff."
    assert any(e.kind == "blocked" and "Sandbox" in e.message for e in ereignisse)


def test_fehlendes_werkzeug_wird_als_fehler_gemeldet(filled_workspace: Workspace) -> None:
    replies = [
        ModelReply(text="", tool_calls=(ToolCall(id="t1", name="gibtsnicht", arguments={}),)),
        ModelReply(text="Okay."),
    ]
    agent, _ = _agent(filled_workspace, replies)
    assert agent.run("Mach was").answer == "Okay."


def test_schrittlimit_bricht_ab(filled_workspace: Workspace) -> None:
    """Endlosschleifen kosten Geld - nach max_steps ist Schluss."""
    endlos = [
        ModelReply(text="", tool_calls=(ToolCall(id=f"t{i}", name="list_files", arguments={}),))
        for i in range(10)
    ]
    agent, _ = _agent(filled_workspace, endlos, max_steps=3)
    result = agent.run("Dreh dich im Kreis")

    assert result.stopped == "schrittlimit"
    assert result.steps == 3
    assert "Abgebrochen" in result.answer


def test_leere_aufgabe_wird_abgelehnt(filled_workspace: Workspace) -> None:
    agent, _ = _agent(filled_workspace, [])
    with pytest.raises(ToolError):
        agent.run("   ")


def test_gespraech_hat_gedaechtnis_und_reset(filled_workspace: Workspace) -> None:
    agent, _ = _agent(filled_workspace, [ModelReply(text="eins"), ModelReply(text="zwei")])
    agent.run("Frage 1")
    agent.run("Frage 2")
    assert len(agent.messages) == 4  # 2x Nutzer + 2x Assistent

    agent.reset()
    assert agent.messages == []
