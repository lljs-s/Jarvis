"""Der Agent: die Schleife aus Denken und Werkzeugbenutzung.

Ablauf einer Aufgabe:

    Aufgabe -> Modell fragen
                 |
                 +-- keine Werkzeuge gewuenscht -> fertig, Antwort zurueck
                 |
                 +-- Werkzeuge gewuenscht -> Risiko pruefen -> ausfuehren
                                              -> Ergebnisse anhaengen
                                              -> wieder Modell fragen ...

Die Schleife ist durch `max_steps` begrenzt, damit ein verwirrter Agent
nicht endlos Tokens (und damit Geld) verbraucht.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from .errors import JarvisError, ToolError, WorkspaceViolation
from .models.base import (
    AssistantMessage,
    Message,
    ModelAdapter,
    ToolCall,
    ToolOutcome,
    ToolResultsMessage,
    Usage,
    UserMessage,
)
from .tools.base import RiskLevel
from .tools.registry import ToolRegistry

SYSTEM_PROMPT = """Du bist Jarvis, ein hilfsbereiter Assistent auf dem Computer des Nutzers.

Arbeitsumgebung:
- Du arbeitest ausschliesslich in einem festen Workspace-Ordner. Alle Pfade,
  die du nennst oder benutzt, sind relativ zu diesem Ordner.
- Ausserhalb des Workspace kannst du technisch nichts erreichen. Versuche es
  gar nicht erst; sag dem Nutzer stattdessen, dass er die Datei in den
  Workspace legen soll.
- In dieser Ausbaustufe kannst du nur LESEN: auflisten, lesen, suchen.
  Du kannst weder Dateien schreiben oder aendern noch Programme ausfuehren
  noch ins Internet. Wenn die Aufgabe das braucht, sag es klar und biete an,
  den Text stattdessen in der Antwort auszugeben.

Arbeitsweise:
- Rate nie den Inhalt einer Datei. Lies sie mit einem Werkzeug oder sag, dass
  du sie nicht kennst.
- Wenn du nicht weisst, welche Dateien es gibt, benutze zuerst list_files.
- Nenne bei Aussagen ueber Dateien immer den Dateinamen, damit der Nutzer
  nachvollziehen kann, woher etwas stammt.
- Antworte auf Deutsch, kurz und konkret.
"""


@dataclass
class AgentEvent:
    """Kleine Nachricht ueber das, was gerade passiert (fuer die Anzeige)."""

    kind: str  # "thinking" | "tool" | "blocked" | "error"
    message: str


@dataclass
class AgentResult:
    """Ergebnis einer Aufgabe."""

    answer: str
    steps: int = 0
    tool_calls: int = 0
    usage: Usage = field(default_factory=Usage)
    stopped: str = "fertig"  # "fertig" | "schrittlimit"


class Agent:
    """Ein einzelner Agent mit Modell, Werkzeugen und Gespraechsverlauf."""

    def __init__(
        self,
        *,
        model: ModelAdapter,
        tools: ToolRegistry,
        system_prompt: str = SYSTEM_PROMPT,
        max_steps: int = 12,
        max_risk: RiskLevel = RiskLevel.LOW,
        on_event: Callable[[AgentEvent], None] | None = None,
        name: str = "jarvis",
    ) -> None:
        self.model = model
        self.tools = tools
        self.system_prompt = system_prompt
        self.max_steps = max_steps
        self.max_risk = max_risk
        self.name = name
        self._on_event = on_event
        self.messages: list[Message] = []

    # -- oeffentlich -------------------------------------------------------

    def reset(self) -> None:
        """Vergisst das bisherige Gespraech."""
        self.messages = []

    def run(self, task: str) -> AgentResult:
        """Bearbeitet eine Aufgabe und liefert die Antwort."""
        if not task.strip():
            raise ToolError("Die Aufgabe ist leer.")

        self.messages.append(UserMessage(text=task.strip()))
        result = AgentResult(answer="")

        for step in range(1, self.max_steps + 1):
            result.steps = step
            reply = self.model.complete(
                system=self.system_prompt,
                messages=self.messages,
                tools=self.tools.specs(),
            )
            result.usage = result.usage + reply.usage
            self.messages.append(AssistantMessage(reply=reply))

            if reply.text:
                self._emit("thinking", reply.text)

            if not reply.wants_tools:
                result.answer = reply.text or "(Das Modell hat nichts geantwortet.)"
                return result

            outcomes = []
            for call in reply.tool_calls:
                result.tool_calls += 1
                outcomes.append(self._execute(call))
            self.messages.append(ToolResultsMessage(outcomes=tuple(outcomes)))

        # Schrittlimit erreicht: lieber sauber abbrechen als endlos weiterlaufen.
        result.stopped = "schrittlimit"
        result.answer = (
            f"Abgebrochen: Nach {self.max_steps} Schritten war die Aufgabe noch nicht fertig. "
            "Formuliere sie kleiner oder erhoehe JARVIS_MAX_STEPS in der .env."
        )
        return result

    # -- intern -----------------------------------------------------------

    def _execute(self, call: ToolCall) -> ToolOutcome:
        """Fuehrt einen Werkzeugaufruf aus - mit Risikopruefung und Fehlerfang."""
        try:
            tool = self.tools.get(call.name)
        except ToolError as exc:
            self._emit("error", str(exc))
            return ToolOutcome(call_id=call.id, content=f"FEHLER: {exc}", is_error=True)

        if tool.risk > self.max_risk:
            message = (
                f"{tool.name} hat Risikostufe {tool.risk.label} und braucht die ausdrueckliche "
                f"Bestaetigung des Nutzers. Das Bestaetigungs-Gate kommt in Etappe 2; "
                "bis dahin ist die Aktion nicht verfuegbar."
            )
            self._emit("blocked", message)
            return ToolOutcome(call_id=call.id, content=f"ABGELEHNT: {message}", is_error=True)

        self._emit("tool", f"{tool.name}({_short(call.arguments)})")
        try:
            result = tool.run(**call.arguments)
        except WorkspaceViolation as exc:
            # Sandbox-Verstoss: das Modell erfaehrt den Grund und kann es
            # richtig machen - abgebrochen wird die Aufgabe deswegen nicht.
            self._emit("blocked", f"Sandbox: {exc}")
            return ToolOutcome(call_id=call.id, content=f"VERBOTEN: {exc}", is_error=True)
        except ToolError as exc:
            self._emit("error", str(exc))
            return ToolOutcome(call_id=call.id, content=f"FEHLER: {exc}", is_error=True)
        except JarvisError as exc:  # pragma: no cover - Sicherheitsnetz
            self._emit("error", str(exc))
            return ToolOutcome(call_id=call.id, content=f"FEHLER: {exc}", is_error=True)

        return ToolOutcome(call_id=call.id, content=result.content, is_error=result.is_error)

    def _emit(self, kind: str, message: str) -> None:
        if self._on_event is not None:
            self._on_event(AgentEvent(kind=kind, message=message))


def _short(arguments: dict[str, object], limit: int = 80) -> str:
    """Werkzeugargumente kurz und lesbar fuer die Anzeige."""
    text = ", ".join(f"{k}={v!r}" for k, v in arguments.items())
    return text if len(text) <= limit else text[: limit - 3] + "..."
