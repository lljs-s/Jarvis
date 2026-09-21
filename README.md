# Jarvis

Ein lokaler Assistent, in dem mehrere KI-Modelle als Agents zusammenarbeiten.
Alle Agents arbeiten **ausschliesslich** in einem festen Workspace-Ordner;
riskante Aktionen brauchen die Bestaetigung des Nutzers.

Aktueller Stand: **Etappe 1** - ein Agent, das Anthropic-Modell und drei
**nur lesende** Datei-Werkzeuge, bedienbar ueber die Kommandozeile.
Schreiben, Code-Ausfuehrung und Netzwerk gibt es noch nicht (siehe `ROADMAP.md`).

## Installation (Windows)

```bat
git clone https://github.com/lljs-s/Jarvis.git
cd Jarvis

python -m venv .venv
.venv\Scripts\activate

pip install -e ".[dev]"

copy .env.example .env
notepad .env          :: ANTHROPIC_API_KEY eintragen, speichern
```

Unter Linux/macOS: `source .venv/bin/activate` und `cp .env.example .env`.

Den API-Key bekommst du unter <https://console.anthropic.com> -> API Keys.
Die Datei `.env` wird von Git ignoriert und verlaesst deinen Rechner nicht.

## Ausprobieren

```bat
jarvis doctor
```
Prueft die Einrichtung (Key, Workspace, Modell, Werkzeuge). Kostet nichts,
ruft die API nicht auf.

```bat
echo Physik-Hausaufgabe bis Freitag > workspace\todo.txt
jarvis workspace
jarvis ask "Was steht in todo.txt?"
```

```bat
jarvis chat
```
Gespraech mit Gedaechtnis. `reset` vergisst den Verlauf, `exit` beendet.

Probier ruhig auch aus, was **nicht** geht:

```bat
jarvis ask "Lies C:\Windows\win.ini und fasse die Datei zusammen"
```
Jarvis kommt nicht an die Datei heran - der Workspace-Waechter blockiert den
Zugriff und meldet das dem Modell, das daraufhin erklaert, dass es die Datei
nur im Workspace lesen kann.

## Einstellungen

Alles steht in der `.env` (Vorlage: `.env.example`):

| Variable | Bedeutung | Standard |
|---|---|---|
| `ANTHROPIC_API_KEY` | dein API-Schluessel | - |
| `JARVIS_WORKSPACE_DIR` | Arbeitsordner der Agents | `workspace` |
| `JARVIS_MODEL` | Modell-ID | `claude-opus-5` |
| `JARVIS_MAX_TOKENS` | maximale Antwortlaenge | `16000` |
| `JARVIS_MAX_STEPS` | Werkzeugrunden pro Aufgabe | `12` |
| `JARVIS_MAX_READ_BYTES` | groesstes Stueck Datei am Stueck | `200000` |

Guenstiger testen: `JARVIS_MODEL=claude-haiku-4-5`.

## Tests

```bat
pytest
```
Laufen ohne Internet und ohne API-Kosten - das Modell wird in den Tests durch
ein `FakeModel` ersetzt. Schwerpunkt sind Ausbruchsversuche aus dem Workspace
(`tests/test_workspace.py`).

## Projektunterlagen

- `CLAUDE.md` - Architektur, Konventionen, Sicherheitsregeln
- `ROADMAP.md` - alle Etappen als Checkliste
