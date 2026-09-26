# Jarvis

Eine lokale KI-Zentrale fuer Windows: ein Chat in der Mitte, Module links,
Agents rechts. Laeuft ausschliesslich auf deinem Rechner.

**Stand: Etappe 1 von 8.** Die Oberflaeche steht, der Server ist abgesichert -
**aber es ist noch kein KI-Modell angeschlossen.** Jarvis antwortet mit einem
Platzhalter. Das echte Modell (Gemini) kommt in Etappe 3.

---

## Einrichten (einmalig)

Du brauchst **Python 3.11 oder neuer** (https://python.org, beim Installieren
"Add Python to PATH" ankreuzen) und **Node.js 20 oder neuer**
(https://nodejs.org).

PowerShell im Projektordner oeffnen und der Reihe nach:

```powershell
# 1. Python-Umgebung anlegen und aktivieren
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Jarvis und die Entwicklungswerkzeuge installieren
pip install -e ".[dev]"

# 3. Einstellungsdatei aus der Vorlage anlegen
Copy-Item .env.example .env

# 4. Pakete der Oberflaeche installieren
cd frontend
npm install
cd ..
```

> **Falls Schritt 1 mit "Die Ausfuehrung von Skripten ist auf diesem System
> deaktiviert" abbricht:** einmalig erlauben mit
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`
> und dann Schritt 1 wiederholen.

## Starten

```powershell
.\.venv\Scripts\Activate.ps1
jarvis dev
```

Oder einfach `.\start.ps1` - das prueft die Einrichtung und startet dasselbe.

Im Terminal erscheint ein Kasten mit einem Link, etwa:

```
Oeffne im Browser:
  http://127.0.0.1:5173/?token=xY7k...
```

**Diesen Link im Browser oeffnen.** Der Token darin ist dein Schluessel -
ohne ihn antwortet Jarvis nicht. Bei jedem Neustart gibt es einen neuen.

Beenden mit **Strg+C** im Terminal.

## Ausprobieren

| Taste | Was passiert |
|---|---|
| `Strg+K` | Befehlspalette - alles von hier erreichbar |
| `Strg+J` | Sprung ins Chatfeld |
| `Strg+B` | Seitenleiste ein/aus |
| `Strg+E` | Agents-Tab ein/aus |
| `Strg+Shift+L` | hell / dunkel |
| `Strg+,` | Einstellungen (hier sind alle Kuerzel aenderbar) |
| `F1` | Hilfe im Chat |

Im Chat funktionieren `/hilfe`, `/opus`, `/agent`, `/modul`.
Tippe `/` und du siehst alle Befehle.

## Wenn etwas nicht klappt

| Problem | Ursache und Loesung |
|---|---|
| Browser zeigt "Der Sitzungs-Token fehlt oder ist abgelaufen" | Der Server wurde neu gestartet. Nimm den **neuen** Link aus dem Terminal. |
| Seite bleibt weiss | Laeuft `jarvis dev` noch? Steht im Terminal ein Fehler? |
| "npm wurde nicht gefunden" | Node.js installieren und PowerShell neu oeffnen. |
| "Die Pakete der Oberflaeche fehlen" | `cd frontend`, `npm install`, `cd ..` |
| Port 8765 oder 5173 belegt | In der `.env` `JARVIS_PORT` bzw. `JARVIS_UI_DEV_PORT` aendern. |
| `jarvis` wird nicht gefunden | Umgebung aktivieren: `.\.venv\Scripts\Activate.ps1` |
| Chat sagt "Keine Verbindung" | Der Python-Server laeuft nicht mehr - Terminal ansehen. |

`jarvis doctor` prueft die Einrichtung und sagt dir, was fehlt. Kostet nichts.

## Wo liegen meine Daten?

Im Ordner **`D:\Jarvis-Workspace`** (eingestellt in der `.env` mit
`JARVIS_WORKSPACE_DIR`) - also ausserhalb dieses Projektordners, damit deine
Dateien nie versehentlich in einem Commit landen. Ohne diese Zeile nimmt Jarvis
`Dokumente\Jarvis-Workspace`.

> **Speicherplatz:** Laufwerk C: ist fast voll. Alles, was Platz braucht,
> liegt auf D: - Projekt (`D:\Projekte\Jarvis`, mit `.venv` und
> `node_modules`), Workspace, die Caches von pip und npm (`D:\Caches`) und
> die temporaeren Dateien (`TEMP`/`TMP` = `D:\Temp`).

Im Projekt liegt nur `test-workspace/` mit Dummy-Dateien zum Ausprobieren.

**Jarvis kommt aus diesem Ordner nicht heraus.** Jeder Pfad laeuft durch den
Workspace-Waechter (`src/jarvis/workspace.py`); rund 60 Tests versuchen
gezielt, ihn auszutricksen.

## Tests

```powershell
pytest                          # Python: 175 Tests
cd frontend; npm test; cd ..    # Oberflaeche: 61 Tests
mypy src; ruff check src tests  # Typen und Stil
```

Alle Tests laufen **ohne Internet und ohne API-Kosten**.

## Wie es weitergeht

Siehe `ROADMAP.md`. Als Naechstes: Etappe 2, das Modulsystem.
Technische Entscheidungen und Regeln stehen in `CLAUDE.md`.
