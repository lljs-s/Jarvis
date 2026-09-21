# ROADMAP - Jarvis

Wir bauen in Etappen. Eine Etappe gilt erst als fertig, wenn sie **Tests hat**
und der Nutzer sie **selbst ausprobiert** hat.

Legende: `[x]` fertig · `[ ]` offen · `( )` bewusst spaeter

---

## Etappe 0 - Setup [x]

- [x] Ordnerstruktur (`src/jarvis/`, `tests/`, `workspace/`)
- [x] Git-Repository, Branch `claude/jarvis-multi-agent-orchestrator-29zoex`
- [x] `.gitignore` (schuetzt `.env`, `workspace/`, Caches)
- [x] `.env.example` als Vorlage, `.env` niemals im Repo
- [x] `pyproject.toml`: Abhaengigkeiten, `jarvis`-Befehl, pytest/mypy/ruff
- [x] `CLAUDE.md` (Projektgedaechtnis) und `ROADMAP.md` (diese Datei)
- [x] `README.md` mit Start-Anleitung

## Etappe 1 - Ein Agent, ein Modell, sichere Datei-Werkzeuge, CLI [x]

- [x] **Workspace-Waechter** (`workspace.py`): einzige Tuer zum Dateisystem
- [x] Werkzeug-Basis mit Risikostufen (`tools/base.py`, `tools/registry.py`)
- [x] Lese-Werkzeuge: `list_files`, `read_file`, `search_text` (alle LOW)
- [x] Modell-Adapter-Schicht (`models/base.py`) + Anthropic-Adapter
- [x] Agent-Schleife mit Schrittlimit und Risiko-Sperre (`agent.py`)
- [x] CLI: `doctor`, `workspace`, `ask`, `chat`, `version`
- [x] Tests: 65 Stueck, davon ~20 gezielte Ausbruchsversuche; laufen ohne Netz
- [x] Fehlermeldungen, die erklaeren, was zu tun ist (fehlender Key, falsches Modell)

**Bewusst ausgeklammert:** Schreiben von Dateien. Es gibt in Etappe 1 kein
sicheres "Ja" des Nutzers - das kommt mit dem Approval-Gate.

## Etappe 2 - Risikostufen, Approval-Gate, Diff, Logbuch, Kosten [ ]

- [ ] `safety/approval.py`: Gate, das HIGH-Aktionen vorlegt (Plan + Vorschau)
- [ ] Schreib-Werkzeuge: `write_file` (neu = MEDIUM), `edit_file`,
      `delete_file` (ueberschreiben/loeschen = HIGH)
- [ ] Diff-Vorschau vor jeder Aenderung (`difflib`, farbig via rich)
- [ ] Automatisches Backup vor Ueberschreiben (`.jarvis-backup/`)
- [ ] `journal/`: SQLite + lesbare JSONL-Datei
      (Zeit, Agent, Modell, Aktion, Risiko, Ergebnis)
- [ ] `costs/`: Tokens -> Preis je Modell, Limit pro Aufgabe und pro Tag,
      Abbruch bei Ueberschreitung
- [ ] CLI: `jarvis log`, `jarvis costs`
- [ ] Tests: Gate laesst HIGH ohne Bestaetigung nie durch; Limits greifen

## Etappe 3 - Model-Adapter + zweites Modell [ ]

- [ ] `models/openai_model.py` (oder `ollama_model.py` fuer lokal/kostenlos)
- [ ] Modell-Registry + Auswahl pro Agent in der `.env`
- [ ] Preistabelle je Anbieter im Kostenzaehler
- [ ] Tests: gleiche Aufgabe, zwei Adapter, gleiches Verhalten der Schleife
- ( ) Midjourney/Bildmodelle: erst wenn Text-Adapter stabil sind

## Etappe 4 - Orchestrator, Worker, Reviewer [ ]

- [ ] `orchestrator/planner.py`: Aufgabe -> Teilschritte (als Datenstruktur)
- [ ] Worker-Rollen mit eigenen Prompts und Werkzeugen
      (Recherche, Schreiben, Code, Pruefung)
- [ ] `orchestrator/reviewer.py`: prueft Ergebnisse vor der Vorlage
- [ ] Plan wird dem Nutzer vor der Ausfuehrung gezeigt
- [ ] Guenstige Modelle fuer einfache Worker, starke fuer schwere Schritte
- [ ] Tests: Zerlegung, Weiterreichen von Ergebnissen, Reviewer lehnt ab

## Etappe 5 - Gedaechtnis [ ]

- [ ] Fruehere Aufgaben, Ergebnisse und Notizen in SQLite
- [ ] Suche (erst Volltext, dann bei Bedarf semantisch)
- [ ] Agent kann gezielt im Gedaechtnis nachschlagen (Werkzeug `recall`)
- [ ] Tests: Wiederfinden, Datenschutz (nichts ausserhalb des Workspace)

## Etappe 6 - Lokale Web-Oberflaeche [ ]

- [ ] `server/`: FastAPI, nur auf 127.0.0.1
- [ ] Chat, Live-Schritte, Diff-Ansicht, Approval-Buttons, Kosten-Anzeige
- [ ] Logbuch durchsuchbar
- [ ] Tests: API-Endpunkte; Sandbox gilt auch hier

## Etappe 7 - Haertung [ ]

- [ ] Einheitliche Fehlerbehandlung, Wiederholversuche mit Backoff
- [ ] Zeitlimits fuer Modelle und Werkzeuge
- [ ] Testabdeckung messen, Luecken schliessen
- [ ] `ruff` + `mypy --strict` sauber, evtl. als Git-Hook
- [ ] Anleitung: Sicherung, Update, Fehlersuche

---

## Naechster Schritt

**Etappe 2**, in dieser Reihenfolge:
1. Approval-Gate + Diff-Vorschau (damit Schreiben ueberhaupt sicher wird)
2. Schreib-Werkzeuge dahinter
3. Logbuch
4. Kostenzaehler mit Limits
