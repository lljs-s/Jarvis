# CLAUDE.md - Projektgedaechtnis fuer Jarvis

> Diese Datei wird zu Beginn jeder Session gelesen. Sie beschreibt, **was**
> Jarvis ist, **wie** es gebaut ist und **welche Regeln** unverhandelbar sind.
> Bei Aenderungen an Architektur oder Regeln: diese Datei mit aktualisieren.

## 1. Projektziel

Eine lokale Anwendung (Windows, Python), in der mehrere KI-Modelle als Agents
zusammenarbeiten:

- Ein **Orchestrator ("Jarvis")** nimmt Aufgaben entgegen, zerlegt sie und
  verteilt sie an **Worker-Agents** (Recherche, Schreiben, Code, Pruefung).
- Modelle haengen hinter einer **einheitlichen Adapter-Schicht**:
  zuerst Anthropic, spaeter OpenAI, Midjourney, lokale Modelle via Ollama.
- Alle Agents arbeiten **ausschliesslich im Workspace-Ordner**.
- **Human-in-the-loop:** jede Aktion hat eine Risikostufe; HIGH braucht die
  ausdrueckliche Bestaetigung des Nutzers, mit Plan und Diff-Vorschau vorab.
- Jede Aktion landet im **Logbuch**; **API-Kosten** werden gezaehlt und begrenzt.

**Der Nutzer ist Schueler mit Programmier-Grundkenntnissen.** Entscheidungen
kurz und verstaendlich begruenden. Lieber einmal zu viel nachfragen als falsch
weiterbauen.

## 2. Architektur

```
        Nutzer
          |  CLI (jetzt)  /  lokale Web-UI (Etappe 6)
+---------v-------------------------------------------+
|  SCHNITTSTELLE   cli.py  ->  spaeter server/ + ui/   |
+------------------------------------------------------+
|  AGENT           agent.py  (Denken <-> Werkzeuge)    |
|                  spaeter orchestrator/ (Jarvis +     |
|                  Worker + Reviewer)                  |
+---------------+------------------+-------------------+
|  MODELLE      |  WERKZEUGE       |  SICHERHEIT/LOG   |
|  models/      |  tools/          |  (ab Etappe 2)    |
|  base.py      |  base.py         |  safety/  Risiko  |
|  anthropic_   |  registry.py     |  journal/ SQLite  |
|  model.py     |  files.py        |  costs/   Limits  |
+---------------+------------------+-------------------+
|  WORKSPACE-WAECHTER   workspace.py                   |
|  Einzige Tuer zum Dateisystem. Jeder Pfad wird hier  |
|  geprueft; alles andere ist WorkspaceViolation.      |
+------------------------------------------------------+
```

### Ordner

```
src/jarvis/
  config.py       Einstellungen aus .env (pydantic-settings, typisiert)
  errors.py       JarvisError, ConfigError, WorkspaceViolation, ToolError, ModelError
  workspace.py    Der Waechter. Einzige Stelle, die Pfade aufloest.
  models/
    base.py       Neutrale Typen: Message, ModelReply, ToolCall, ToolOutcome, Usage
    anthropic_model.py   Adapter fuer das `anthropic`-SDK
  tools/
    base.py       Tool (ABC), RiskLevel, ToolResult
    registry.py   ToolRegistry: Namen -> Werkzeuge, Specs fuers Modell
    files.py      list_files, read_file, search_text (alle LOW/lesend)
  agent.py        Die Schleife: Modell fragen -> Werkzeuge -> wiederholen
  cli.py          typer-CLI: doctor, workspace, ask, chat, version
tests/            pytest; Schwerpunkt Sandbox-Ausbruchsversuche
workspace/        Arbeitsordner der Agents (gitignored)
```

### Warum schlanke Eigenloesung statt Framework

Entschieden in Session 1: nur das offizielle `anthropic`-SDK plus eigene
Werkzeugschleife - **kein** Claude Agent SDK, **kein** LangGraph.
Gruende: (1) das Projekt soll mehrere Anbieter hinter EINER eigenen
Adapter-Schicht bedienen, ein anbieterspezifisches Agent-Framework arbeitet
dagegen; (2) Sandbox und Approval-Gate muessen technisch erzwungen sein -
das geht nur, wenn kein Framework an uns vorbei Dateien anfasst;
(3) Lernwert: jeder Schritt ist sichtbarer eigener Code.
LangGraph darf in Etappe 4 neu bewertet werden, falls der Orchestrator-Graph
wirklich komplex wird.

## 3. Sicherheitsregeln (unverhandelbar)

1. **Kein Dateizugriff ausserhalb des Workspace.** Werkzeuge rufen
   `Workspace.resolve()` / `resolve_file()` auf - niemals selbst `open()`,
   `Path(...)`-Basteleien oder `os.path.join` mit Modell-Eingaben.
   Abgewehrt werden: `..`, absolute Unix- und Windows-Pfade, UNC-Pfade, `~`,
   Null-Bytes, unter Windows reservierte Namen und Symlinks nach draussen.
2. **Risikostufen.** LOW = nur lesen. MEDIUM = neue Dateien anlegen,
   Netzwerk lesen. HIGH = ueberschreiben, loeschen, Code ausfuehren,
   teure API-Aufrufe. Der Agent fuehrt nur Werkzeuge bis `max_risk` aus;
   alles darueber wird abgelehnt (ab Etappe 2: zur Bestaetigung vorgelegt).
3. **Keine Geheimnisse im Repo.** API-Keys nur aus `.env` (gitignored),
   im Code als `SecretStr`. Keys nie loggen, nie in Fehlermeldungen ausgeben.
4. **Sicherheitsbremsen.** `max_steps` begrenzt die Werkzeugrunden pro
   Aufgabe, `max_read_bytes` die Dateigroesse. Ab Etappe 2 zusaetzlich
   Kostenlimit pro Aufgabe und pro Tag.
5. **Fehler des Modells sind keine Abstuerze.** Sandbox-Verstoesse und
   Werkzeugfehler gehen als `is_error`-Werkzeugergebnis zurueck ans Modell,
   damit es sich korrigieren kann. Nur Konfig- und API-Fehler brechen ab.

## 4. Konventionen

- **Python >= 3.11**, `from __future__ import annotations` in jeder Datei,
  vollstaendige Typannotationen, Dataclasses statt loser Dicts.
- **Abhaengigkeiten sparsam:** `anthropic`, `pydantic-settings`, `typer`,
  `rich`; dev: `pytest`, `mypy`, `ruff`. Neue Abhaengigkeit = kurze Begruendung.
- **Sprache:** Code, Bezeichner und Docstrings so, wie sie hier stehen
  (Docstrings/Kommentare auf Deutsch, ohne Umlaute in Quelltextkommentaren,
  damit es unter Windows keine Encoding-Ueberraschungen gibt). Nutzertexte
  der CLI auf Deutsch.
- **Modelle** werden nie im Code fest verdrahtet, sondern kommen aus `.env`
  (`JARVIS_MODEL`). Standard: `claude-opus-5`.
- **Tests zu jeder Etappe.** Neue Faehigkeit ohne Test = nicht fertig.
  Tests laufen ohne Netz und ohne API-Kosten (FakeModel in `tests/test_agent.py`).
- **Commits** klein und sprechend, auf dem vereinbarten Branch.

## 5. Stand (nach Session 1)

Fertig: Etappe 0 (Setup) und Etappe 1 (ein Agent, ein Modell, sichere
Lese-Werkzeuge, CLI, 65 Tests). Details und naechste Schritte: `ROADMAP.md`.

**Bewusst noch nicht da:** Schreiben/Loeschen von Dateien, Code-Ausfuehrung,
Netzwerkzugriff, Approval-Gate, Logbuch, Kostenzaehler, zweites Modell,
Orchestrator, Gedaechtnis, Web-UI.

## 6. Befehle

```bash
python -m venv .venv                  # einmalig
.venv\Scripts\activate                # Windows (Linux: source .venv/bin/activate)
pip install -e ".[dev]"               # Projekt + Entwicklungswerkzeuge
copy .env.example .env                # Windows (Linux: cp)

jarvis doctor                         # Einrichtung pruefen (kostenlos)
jarvis workspace                      # Workspace-Inhalt zeigen
jarvis ask "Was steht in todo.txt?"   # eine Aufgabe
jarvis chat                           # Gespraech mit Gedaechtnis

pytest                                # alle Tests (ohne Netz, ohne Kosten)
mypy src && ruff check src            # Typen und Stil
```
