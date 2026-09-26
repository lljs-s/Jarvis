# ROADMAP - Jarvis

Wir bauen in Etappen. Eine Etappe gilt erst als fertig, wenn sie **Tests hat**
und der Nutzer sie **selbst ausprobiert** hat.

Legende: `[x]` fertig · `[ ]` offen · `( )` bewusst spaeter

---

## Etappe 0 - Setup [x]

- [x] Ordnerstruktur (`src/jarvis/`, `frontend/`, `tests/`, `test-workspace/`)
- [x] Git-Repository, Branch `claude/trusting-ramanujan-ob7n4g`
- [x] `.gitignore` schuetzt `.env`, `workspace/`, `node_modules/`, Caches
- [x] `.env.example` als Vorlage, `.env` niemals im Repo
- [x] `pyproject.toml`: Abhaengigkeiten, `jarvis`-Befehl, pytest/mypy/ruff
- [x] `frontend/package.json`: React, Vite, Vitest
- [x] `CLAUDE.md` (Projektgedaechtnis) und `ROADMAP.md` (diese Datei)
- [x] `README.md` mit Windows-Startanleitung

## Etappe 1 - Grundgeruest der Oberflaeche [x]

**Kern (aus Session 1, jetzt nach `core/` umgezogen)**
- [x] Workspace-Waechter: einzige Tuer zum Dateisystem
- [x] Werkzeug-Basis mit Risikostufen, Registry
- [x] Lese-Werkzeuge: `list_files`, `read_file`, `search_text` (alle LOW)
- [x] Modell-Adapter-Schicht + Anthropic-Adapter
- [x] Agent-Schleife mit Schrittlimit und Risiko-Sperre
- [x] CLI: `doctor`, `workspace`, `ask`, `chat`, `version`

**Neu in Session 2**
- [x] Waechter fuer Windows gehaertet: Laufwerke, UNC, reservierte Namen,
      Punkte/Leerzeichen am Ende, ADS, Junctions, Gross-/Kleinschreibung
- [x] Echter Workspace ausserhalb des Projekts (`Dokumente\Jarvis-Workspace`),
      im Repo nur `test-workspace/` mit Dummy-Dateien
- [x] FastAPI-Server auf 127.0.0.1: `/api/health`, `/api/settings`,
      `/api/agents`, `/api/modules`, WebSocket `/ws/chat`
- [x] Absicherung: Sitzungs-Token, Origin-Pruefung, Host-Pruefung,
      nur Loopback, keine oeffentliche API-Doku
- [x] React-Oberflaeche: Seitenleiste (Module), Jarvis-Chat in der Mitte,
      Agents-Tab rechts, Statusleiste mit Workspace/Kosten/Modell
- [x] Befehlspalette (Strg+K), Fokus-Sprung (Strg+J), Panels umschalten,
      hell/dunkel, Einstellungsdialog
- [x] Tastenkuerzel in den Einstellungen aenderbar, im Browser gespeichert
- [x] Slash-Befehle `/opus`, `/agent`, `/modul`, `/hilfe` mit Vorschlaegen
- [x] Alles per Tastatur erreichbar, Modulbaum als `role="tree"`
- [x] `jarvis dev` startet Server + Oberflaeche und zeigt den Link mit Token
- [x] Tests: 159 Python + 57 Frontend, ohne Netz und ohne Kosten
- [x] Kosten intern in USD, Anzeige in EUR ueber `JARVIS_USD_TO_EUR`

**Bewusst ausgeklammert:** Jarvis antwortet noch mit einem Platzhalter -
es ist kein Modell angeschlossen.

## Etappe 2 - Modulsystem [ ] (gebaut, wartet auf deinen Test)

Datenmodell: siehe `CLAUDE.md`, Abschnitt 5.

- [x] Doku: Datenmodell, Schema-Versionen, Trading-Regel
- [x] Kern: Datenschutzstufen `offen` < `vertraulich` < `lokal`,
      `folder.json` / `module.json` / Typ-Definitionen lesen,
      Modulbaum aus `<Workspace>\bereiche\` mit Vererbung
- [x] Kern: Bereiche und Module anlegen, umbenennen, verschieben
      (mit `datenschutz_grund`), Stufe setzen und bewusst senken
- [x] Schranken: Werkzeuge duerfen `folder.json`/`module.json`/`.jarvis`
      nie schreiben; Lese-Werkzeuge zeigen Cloud-Modellen nur `offen`
- [x] Server: REST-Endpunkte fuer Baum, Typen und alle Aenderungen
- [x] Demo "Beispiel" (Repo + echter Workspace), im echten Workspace
      zusaetzlich "Unternehmen" und "Trading" als `vertraulich`
- [x] Oberflaeche: "+" (Neuer Ordner / Neues Modul mit Typauswahl), F2,
      Drag & Drop, Verschieben per Tastatur, Datenschutz mit Herkunft
- [x] Start-Typen: Notizen, Recherche, Aufgaben, Dateien
- [x] Tests fuer jede Schranke (432 gesamt: 350 Python + 82 Frontend)
- [ ] **Du probierst es selbst aus** - danach ist die Etappe fertig
- [ ] Offen: Widgets zeigen die Modulinhalte an (Notizliste, Editor,
      Aufgabenliste, Dateiliste). Das Widget-Register im Kern steht, die
      Anzeige in der Oberflaeche fehlt noch - vor oder mit Etappe 3 klaeren

## Etappe 3 - Erste KI-Anbindung [ ]

- [ ] Start mit dem **vorhandenen Anthropic-Adapter**: Chat in der
      Oberflaeche mit echtem Modell, Antwort Wort fuer Wort ueber den WebSocket
- [ ] `core/models/gemini_model.py` als **zweiter Adapter** hinter derselben
      Adapter-Schicht
- [ ] Welches Modell die zentrale Rolle (Jarvis) uebernimmt, ist eine
      **Einstellung**, nie im Code
- [ ] Werkzeugaufrufe sichtbar im Chat (welches Werkzeug, welche Datei)
- [ ] Tests: beide Adapter mit Attrappe, gleiche Schleife

## Etappe 4 - Sicherheit: Freigabe, Diff, Logbuch, Kosten [ ]

- [ ] `core/safety/approval.py`: Gate, das HIGH-Aktionen vorlegt
- [ ] Schreib-Werkzeuge: `write_file` (neu = MEDIUM), `edit_file`,
      `delete_file` (ueberschreiben/loeschen = HIGH)
- [ ] Diff-Vorschau vor jeder Aenderung, Freigabe-Dialog in der Oberflaeche
- [ ] Freigabe fuer `vertraulich`: zeigt konkret, welche Daten hinausgehen
      (Modul, Dateien, Umfang) - nicht nur "Cloud ja/nein"
- [ ] Automatisches Backup vor Ueberschreiben
- [ ] `core/journal/`: SQLite + lesbare JSONL-Datei (Zeit, Agent, Modell,
      Aktion, Dateien, Ergebnis, Kosten), durchsuchbar in der Oberflaeche
- [ ] `core/costs/`: Tokens -> USD je Modell, Limit pro Aufgabe und pro Tag,
      Abbruch bei Ueberschreitung, Anzeige in EUR
- [ ] Tests: Gate laesst HIGH ohne Bestaetigung nie durch; Limits greifen

## Etappe 5 - Model-Adapter: Opus als Thinktank, Ollama, Datenschutz [ ]

- [ ] Eskalation: Jarvis gibt schwere Aufgaben an Opus ab, kuendigt es an
      und nennt den Grund; `/opus` ruft ihn direkt
- [ ] `core/models/ollama_model.py` (sobald Ollama installiert ist)
- [ ] Rollen (Alltag / Thinktank / lokal) in den Einstellungen zuweisbar
- [ ] Datenschutzstufe `lokal` technisch erzwungen: solche Module duerfen
      nur an Ollama - solange Ollama fehlt, an gar kein Modell
- [ ] Preistabelle je Anbieter im Kostenzaehler
- [ ] Tests: ein Cloud-Modell bekommt ein `lokal`-Modul nie zu sehen

## Etappe 6 - Agents [ ]

- [ ] Agent als Datei (`agent.yaml`): Name, Rolle, Modell, erlaubte
      Werkzeuge, erlaubte Module, max. Risikostufe ohne Rueckfrage
- [ ] "+" fuehrt durch diese Felder, 3 Vorlagen: Recherche, Schreiben, Pruefer
- [ ] "x" loescht mit Bestaetigung
- [ ] `core/orchestrator/`: Aufgabe zerlegen, an Agents verteilen,
      Reviewer-Agent prueft das Ergebnis vor der Vorlage
- [ ] Abteilungen: Module nehmen Auftraege aus anderen Modulen an
      (`.jarvis\auftraege\`), Stufen-Etikett, nie von hoeher nach niedriger
- [ ] Live-Status je Agent in der Oberflaeche
- [ ] ( ) LangGraph neu bewerten, falls der Graph wirklich komplex wird
- [ ] Tests: Zerlegung, Weiterreichen, Reviewer lehnt ab, Berechtigungen

## Etappe 7 - Modellierbares Layout [ ]

- [ ] dockview einbauen: Panels andocken, verschieben, Groesse aendern
- [ ] Layout als JSON speichern - global und optional pro Modul
- [ ] Standardlayout zum Zurucksetzen
- [ ] Tests: Layout speichern, laden, zuruecksetzen

## Etappe 8 - Haertung und Paketierung [ ]

- [ ] Fehlerbehandlung ueberall verstaendlich (was ist passiert, was tun)
- [ ] Grenzfaelle: sehr grosse Dateien, viele Module, langsame Modelle
- [ ] Tauri-Huelle: Jarvis als echte Windows-App (.exe)
- [ ] Server startet mit der App, beendet sich mit ihr
- [ ] Tests: Start, Neustart, Abbruch mitten in einer Aufgabe

## Spaeter (bewusst offen)

- ( ) Gedaechtnis ueber Sessions hinweg (frueher Etappe 5)
- ( ) Bildmodelle (Midjourney)
- ( ) Echte Code-Plugins fuer Module
- ( ) Modultyp **Trading-Journal** - nur Analyse und Dokumentation.
      Agents erhalten **keinen Zugriff auf Broker-Konten** und koennen
      **keine Orders ausloesen** (feste Regel, siehe `CLAUDE.md` 3.6)
- ( ) Modultyp Tabellen
- ( ) Synchronisierung zwischen Geraeten
