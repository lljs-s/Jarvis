# CLAUDE.md - Projektgedaechtnis fuer Jarvis

> Diese Datei wird zu Beginn jeder Session gelesen. Sie beschreibt, **was**
> Jarvis ist, **wie** es gebaut ist und **welche Regeln** unverhandelbar sind.
> Bei Aenderungen an Architektur oder Regeln: diese Datei mit aktualisieren.

## 1. Projektziel

Eine lokale Desktop-Anwendung (**Windows**), in der der Nutzer private und
spaeter berufliche Arbeit buendelt. Mehrere KI-Modelle arbeiten als Agents
zusammen und greifen auf lokal gespeicherte Dateien zu.

- **Jarvis** ist der zentrale Ansprechpartner (Modell: Gemini). Er nimmt
  Aufgaben entgegen, zerlegt sie und verteilt sie an **Worker-Agents**.
- **Claude Opus** ist der **Thinktank** fuer schwere Analyse, Strategie und
  schwierigen Code. Jarvis eskaliert selbstaendig an ihn, kuendigt das im
  Chat an und nennt den Grund. Der Nutzer kann ihn mit `/opus` direkt rufen.
- **Ollama** (lokal) fuer einfache Aufgaben und vertrauliche Daten.
  Noch nicht installiert - kommt in einigen Wochen.
- **Module** buendeln Daten und Widgets; ein Modul ist ein echter Ordner.
- **Human-in-the-loop:** jede Aktion hat eine Risikostufe; HIGH braucht die
  ausdrueckliche Bestaetigung des Nutzers, mit Plan und Diff-Vorschau vorab.
- Jede Aktion landet im **Logbuch**; **API-Kosten** werden gezaehlt und begrenzt.

**Der Nutzer ist Schueler mit Programmier-Grundkenntnissen.** Entscheidungen
kurz und verstaendlich begruenden. Lieber einmal zu viel nachfragen als falsch
weiterbauen.

## 2. Architektur

```
  Browser (Etappe 1-7)   ->   spaeter Tauri-Fenster (Etappe 8)
  React + TypeScript + Vite
        |  REST      Module, Agents, Einstellungen
        |  WebSocket Chat-Strom, Agent-Status, Freigabe-Anfragen
+-------v------------------------------------------------------+
|  server/    FastAPI, ausschliesslich 127.0.0.1                |
|             uebersetzt HTTP <-> Kern. Enthaelt KEINE Logik.   |
+---------------------------------------------------------------+
|  core/      Der Kern - kann alles, weiss nicht, wer fragt      |
|   agent.py        Denken <-> Werkzeuge                         |
|   models/         base.py | anthropic | gemini | ollama        |
|   tools/          registry + Werkzeuge mit Risikostufen        |
|   modules/        module.json lesen, Berechtigungen pruefen    |
|   safety/         Risiko, Freigabe-Gate, Datenschutzstufen     |
|   journal/  costs/  orchestrator/                              |
+---------------------------------------------------------------+
|  workspace.py   DER WAECHTER - einzige Tuer zum Dateisystem    |
+---------------------------------------------------------------+
        |
   D:\Jarvis-Workspace   (ausserhalb des Projekts!)
```

Zwei Tore, durch die **alles** muss: der **Workspace-Waechter** (kein Pfad
nach draussen) und das **Freigabe-Gate** (keine HIGH-Aktion ohne Ja des
Nutzers). Beide sitzen im Kern, nicht im Server - so kann auch die CLI nicht
daran vorbei.

### Ordner

```
src/jarvis/
  config.py       Einstellungen aus .env (pydantic-settings, typisiert)
  errors.py       JarvisError, ConfigError, WorkspaceViolation (+ DatenschutzVerstoss),
                  ModulFehler, ToolError, ModelError
  workspace.py    Der Waechter. Einzige Stelle, die Pfade aufloest.
  core/
    agent.py      Die Schleife: Modell fragen -> Werkzeuge -> wiederholen
    models/       base.py (neutrale Typen), anthropic_model.py
    tools/        base.py (Tool, RiskLevel, KERN_WERKZEUGE), registry.py, files.py
    safety/       datenschutz.py (Stufen, strengste, darf_fliessen)
    modules/      formate.py (folder/module.json), typen.py + typen/*.json,
                  baum.py (lesen + vererben), dienst.py (EINZIGE Schreibstelle),
                  zugriff.py (Schreibsperre, Datenschutz-Filter), demo.py
  server/
    app.py        FastAPI-App, Schichten: CORS -> Tuersteher -> Routen
    security.py   Token, Origin- und Host-Pruefung
    schemas.py    Der Vertrag zum Frontend (= die TS-Typen in lib/api.ts)
    routes/       system.py, agents.py, modules.py
    ws.py         Chat-WebSocket
    start.py      Startlogik fuer `jarvis serve` und `jarvis dev`
  cli.py          typer-CLI: doctor, workspace, ask, chat, serve, dev, version
frontend/
  src/lib/        api.ts, token.ts, chatVerbindung.ts, shortcuts.ts, slash.ts
  src/store/      store.ts (zustand)
  src/components/ Panel, Dialog, CommandPalette, StatusBar
  src/features/   chat/, agents/, modules/ (Sidebar, AnlegenDialog,
                  Eigenschaften, baumhilfen, aenderung), settings/
  src/app/App.tsx Hauptfenster
  src/test-daten.ts  Baukasten fuer KnotenInfo in Tests
tests/            pytest; Schwerpunkt Sandbox- und Server-Angriffe
test-workspace/   Dummy-Dateien + Demo unter bereiche/ (gehoert ins Repo)
```

### Warum dieser Stack

- **FastAPI + React + Vite:** der KI-Teil muss Python sein, die Oberflaeche
  soll modern und tastaturfreundlich sein. Ein WebSocket reicht fuer den
  Chat-Strom.
- **zustand** statt Redux: ein Store ist eine Funktion, kein Baukasten.
- **cmdk** fuer die Befehlspalette, **dockview** ab Etappe 7 fuer andockbare
  Panels - beides bewaehrt, Eigenbau waere hier reine Fehlerquelle.
- **Kein Agent-Framework** (kein Claude Agent SDK, kein LangGraph):
  (1) mehrere Anbieter hinter EINER eigenen Adapter-Schicht, ein
  anbieterspezifisches Framework arbeitet dagegen; (2) Sandbox und
  Approval-Gate muessen technisch erzwungen sein - das geht nur, wenn kein
  Framework an uns vorbei Dateien anfasst; (3) Lernwert.
  LangGraph darf in Etappe 6 neu bewertet werden, falls der
  Orchestrator-Graph wirklich komplex wird.
- **Tauri** erst in Etappe 8: bis dahin ist der Browser schneller zu testen.

## 3. Sicherheitsregeln (unverhandelbar)

### 3.1 Kein Dateizugriff ausserhalb des Workspace

Werkzeuge rufen `Workspace.resolve()` / `resolve_file()` auf - **niemals**
selbst `open()`, `Path(...)`-Basteleien oder `os.path.join` mit
Modell-Eingaben.

Die Pruefung ist zweistufig:
1. `split_relative()` prueft **rein textlich**, ohne Dateisystem. Sie
   verhaelt sich auf jedem Betriebssystem gleich.
2. `Workspace.resolve()` loest auf (Symlinks, Junctions) und prueft mit
   `contains()` erneut, ob das Ergebnis im Workspace liegt.

### 3.2 Windows-Regeln fuer Pfade (feste Regel)

Der Waechter muss **jeden** dieser Faelle ablehnen, und fuer **jeden** muss
es einen Test in `tests/test_workspace_windows.py` geben:

| Fall | Beispiel |
|---|---|
| Laufwerksbuchstaben | `C:\Windows\system.ini`, `c:/windows` |
| laufwerksrelativ | `C:notizen.txt` |
| UNC / Netzwerk | `\\server\freigabe\x`, `\\127.0.0.1\c$` |
| erweiterte Syntax | `\\?\C:\...`, `\\.\pipe\...` |
| reservierte Namen | `CON`, `nul.txt`, `COM1.tar.gz`, `LPT9` |
| Punkt/Leerzeichen am Ende | `bericht.txt.`, `ordner `, `  datei.txt  ` |
| Alternate Data Streams | `datei.txt:geheim` |
| verbotene Zeichen | `< > : " \| ? *`, Steuerzeichen |
| Gross-/Kleinschreibung | `c:\ws` und `C:\WS` sind derselbe Ordner |
| Junctions / Symlinks | `mklink /J` aus dem Workspace hinaus |
| aehnliche Nachbarn | `workspace_geheim` ist kein Teil von `workspace` |

Vergleiche von Pfaden laufen ueber `os.path.commonpath` + `os.path.normcase`,
**nie** ueber Textvergleich - sonst stimmt die Gross-/Kleinschreibung unter
Windows nicht.

Tests, die echte Junctions oder Symlinks brauchen, laufen nur unter Windows
und ueberspringen sich sonst selbst (`nur_windows`). Alle anderen laufen
ueberall.

### 3.3 Absicherung des lokalen Servers (feste Regel)

Jede Webseite im Browser darf Anfragen an `127.0.0.1` schicken. Deshalb gilt
ab Etappe 1 und dauerhaft:

1. **Sitzungs-Token** - beim Start gewuerfelt (`secrets.token_urlsafe`).
   Ohne gueltiges Token antwortet **weder REST noch WebSocket** (401).
   Vergleich immer mit `secrets.compare_digest` (zeitkonstant).
2. **Origin-Pruefung** - nur die eigene Oberflaeche. Beim **WebSocket ist der
   Origin Pflicht**, weil ein WebSocket keiner Same-Origin-Regel unterliegt
   (Cross-Site-WebSocket-Hijacking). Pruefung **vor** `accept()`.
3. **Host-Pruefung** - schuetzt gegen DNS-Rebinding, bei REST und WebSocket.
4. `JARVIS_HOST` laesst nur Loopback-Adressen zu (Validator in `config.py`).
5. `/docs`, `/redoc` und `/openapi.json` bleiben abgeschaltet.
6. Das Frontend bekommt **nie** einen API-Key - nur `hat_..._key: bool`.
   Das Token steht nur in der Adresszeile beim ersten Aufruf, wandert in den
   sessionStorage und wird sofort aus der Adresse entfernt.

Jede dieser Schranken braucht einen Test, der zeigt, dass ein fremder
Absender **abgewiesen** wird - nicht nur, dass der eigene durchkommt.

### 3.4 Wo die Daten liegen (feste Regel)

- Der **echte Workspace liegt ausserhalb des Projektordners**.
  Auf dem Rechner des Nutzers: `D:\Jarvis-Workspace` (per
  `JARVIS_WORKSPACE_DIR` in der `.env`, weil C: fast voll ist).
  Standard ohne Angabe: `Dokumente\Jarvis-Workspace`, unter Windows ueber
  `SHGetKnownFolderPath` ermittelt (wichtig, falls "Dokumente" nach OneDrive
  umgeleitet ist). Umstellbar mit `JARVIS_WORKSPACE_DIR` in der `.env`.
- Im Projekt liegt **nur** `test-workspace/` mit Dummy-Dateien.
- `workspace/` im Projekt ist in `.gitignore` - falls jemand den Pfad doch
  dorthin stellt, landen die Daten trotzdem nicht im Repo.

### 3.5 Risikostufen

LOW = nur lesen. MEDIUM = neue Dateien anlegen, Netzwerk lesen.
HIGH = ueberschreiben, loeschen, Code ausfuehren, teure API-Aufrufe.
Der Agent fuehrt nur Werkzeuge bis `max_risk` aus; alles darueber wird
abgelehnt (ab Etappe 4: zur Bestaetigung vorgelegt).

### 3.6 Weitere Regeln

- **Keine Geheimnisse im Repo.** API-Keys nur aus `.env` (gitignored),
  im Code als `SecretStr`. Keys nie loggen, nie in Fehlermeldungen ausgeben.
- **Sicherheitsbremsen.** `max_steps` begrenzt Werkzeugrunden pro Aufgabe,
  `max_read_bytes` die Dateigroesse, ab Etappe 4 Kostenlimit pro Aufgabe
  und pro Tag.
- **Datenschutzstufen** (Details in Abschnitt 5): `offen` < `vertraulich`
  < `lokal`, im Kern erzwungen, nie nur in der Oberflaeche.
- **Fehler des Modells sind keine Abstuerze.** Sandbox-Verstoesse und
  Werkzeugfehler gehen als `is_error`-Ergebnis zurueck ans Modell, damit es
  sich korrigieren kann. Nur Konfig- und API-Fehler brechen ab.
- **Trading (feste Regel):** Der spaetere Modultyp "Trading-Journal" dient
  nur Analyse und Dokumentation. Agents bekommen **keinen Zugriff auf
  Broker-Konten** und koennen **keine Orders ausloesen** - es gibt dafuer
  weder Werkzeug noch Schnittstelle, und ein Modultyp kann keine Werkzeuge
  anfordern, die der Kern nicht selbst mitbringt.

## 4. Konventionen

- **Python >= 3.11**, `from __future__ import annotations` in jeder Datei,
  vollstaendige Typannotationen, Dataclasses statt loser Dicts.
- **TypeScript strict**, keine `any`. Die Typen in `frontend/src/lib/api.ts`
  entsprechen genau den Pydantic-Modellen in `server/schemas.py` - wer eines
  aendert, aendert das andere mit.
- **Abhaengigkeiten sparsam.** Python: `anthropic`, `pydantic-settings`,
  `typer`, `rich`, `fastapi`, `uvicorn`; dev: `pytest`, `mypy`, `ruff`,
  `httpx`. Frontend: `react`, `zustand`, `cmdk`, `tailwindcss`;
  dev: `vite`, `vitest`, `@testing-library/*`. Neue Abhaengigkeit =
  kurze Begruendung.
- **Sprache:** Docstrings und Kommentare auf Deutsch, **ohne Umlaute im
  Quelltext** (Encoding-Ruhe unter Windows). Nutzertexte auf Deutsch, dort
  mit Umlauten.
- **Modelle** nie im Code fest verdrahten, immer aus `.env` bzw. den
  Einstellungen.
- **Kosten** werden intern **in USD** gezaehlt (so stehen die Preislisten der
  Anbieter). Die Anzeige rechnet mit `JARVIS_USD_TO_EUR` in EUR um.
- **Betriebssystem:** entwickelt und betrieben wird unter **Windows**.
  Befehle in Doku und Skripten sind PowerShell-Befehle.
- **Ab Session 3 laeuft die Entwicklung lokal auf dem Windows-PC des
  Nutzers**, nicht mehr in einer Cloud-Session. Grund: nur dort laufen die
  fuenf Tests, die echtes Windows brauchen (Junctions, Symlinks,
  NTFS-Gross-/Kleinschreibung, verschiedene Laufwerke) - und genau die
  schuetzen den Workspace. Laeuft eine Session doch einmal in der Cloud,
  gilt: diese fuenf Tests sind dort NICHT bestaetigt, das muss im Ergebnis
  ausdruecklich dastehen, und sie duerfen nie abgeschwaecht werden, nur
  damit sie gruen sind.
- **Stand der Windows-Tests (Session 4, 2026-09-26, Windows 10 Pro 19045,
  Python 3.14, NTFS auf D:):**
  **Alle fuenf echt bestaetigt, 67/67 in `test_workspace_windows.py`,
  175/175 Python-Tests ohne Skip.**
  - `test_gross_kleinschreibung_findet_dieselbe_datei`,
    `test_verschiedene_laufwerke_sind_nie_enthalten`,
    `test_junction_nach_draussen_wird_erkannt`,
    `test_junction_innerhalb_bleibt_erlaubt`
  - `test_dateisymlink_nach_draussen_wird_erkannt` sowie die zwei
    Symlink-Tests in `test_workspace.py`: erst uebersprungen
    (`WinError 1314`, Entwicklermodus war fuer Windows nicht aktiv), nach
    Aus-/Einschalten und Neustart
    (`AllowDevelopmentWithoutDevLicense = 1`) bestanden. Kein Codefehler.
  - Wird einer dieser Tests je wieder uebersprungen: das ist KEIN Gruen.
    Dem Nutzer klar melden (Entwicklermodus pruefen).
- **Speicherplatz:** C: ist fast voll. Projekt, `.venv`, `node_modules`,
  Workspace (`D:\Jarvis-Workspace`), Caches (`D:\Caches`) und TEMP
  (`D:\Temp`) liegen auf D:. Neues, das Platz braucht, ebenfalls nach D:.
  Alles, was C: zusaetzlich belastet (Installationen, globale Pakete,
  Caches ohne Umleitung, Tools mit Daten unter `%USERPROFILE%` oder
  `%LOCALAPPDATA%`), wird dem Nutzer **vorher** angekuendigt.
- **Python 3.14:** Die venv laeuft mit Python 3.14 - sehr neu. Wenn ein
  Paket damit nicht funktioniert (fehlende Wheels, Build-Fehler,
  Inkompatibilitaet), **sofort dem Nutzer melden** und gemeinsam
  entscheiden - **keine Notloesung** (kein Pinnen auf Uraltversionen, kein
  Umgehen, kein stilles Weglassen).
- **Tests zu jeder Etappe.** Neue Faehigkeit ohne Test = nicht fertig.
  Tests laufen ohne Netz und ohne API-Kosten (FakeModel bzw. Attrappen).
- **Commits** klein und sprechend, auf dem vereinbarten Branch (`main`).
  **Nach jedem abgeschlossenen Teilschritt nach GitHub pushen**
  (`origin`, https://github.com/lljs-s/Jarvis) - die Sicherung ausserhalb
  des PCs. Nie force-pushen.

## 5. Datenmodell: Bereiche und Module (ab Etappe 2)

Alles liegt als normale Ordner und JSON-Dateien im Workspace - keine
versteckte Datenbank.

```
<Workspace>\
  bereiche\                  Wurzel des Modulbaums
    folder.json              Grundeinstellungen der Wurzel (Stufe: offen)
    Schule\                  Bereich  = Ordner MIT folder.json
      folder.json
      Mathe\                 Modul    = Ordner MIT module.json (ein Blatt)
        module.json
        notizen\...          Daten des Moduls
  .jarvis\                   Systemdaten (spaeter: eigene Typen, Auftraege)
src\jarvis\core\modules\typen\*.json   eingebaute Modultypen
```

- **Bereich** = Ordner mit `folder.json`, beliebig tief verschachtelt.
  **Modul** = "ein Typ an einem Ort": Ordner mit `module.json`, enthaelt
  nur Daten (keine weiteren Bereiche/Module). Beides zugleich = Fehler.
  Unterordner eines Bereichs ohne JSON werden ignoriert (mit Warnung).
- **Modultypen** sind reine Beschreibungen (Widgets, Startordner,
  Einstellungen, erlaubte Werkzeuge, Mindeststufe) und liegen getrennt von
  den Modulen. Neuer Typ = neue JSON-Datei, kein Umbau des Kerns. Den Code
  der Widgets liefert das Widget-Register im Kern.
- **IDs statt Pfade:** Jeder Bereich und jedes Modul hat eine feste,
  zufaellige `id` (`ord_...`, `mod_...`). Umbenennen/Verschieben aendert
  sie nie. Verweise (Auftraege, spaeter Layouts) nutzen nur die `id`.
  Doppelte ids (z. B. im Explorer kopiert) werden repariert: das zweite
  Exemplar bekommt eine neue.
- **Anzeigename = Ordnername**, geprueft vom Waechter.

### 5.1 Datenschutzstufen

| Stufe | Rang | Wer darf die Daten sehen? |
|---|---|---|
| `offen` | 0 | alle Modelle, auch Cloud |
| `vertraulich` | 1 | Cloud nur nach Freigabe pro Aufgabe. Die Freigabe zeigt **konkret**, was hinausgeht (Modul, Dateien, Umfang), nicht nur "Cloud ja/nein" (Etappe 4) |
| `lokal` | 2 | nur Ollama; solange Ollama fehlt: **kein Modell** |

Bis das Freigabe-Gate existiert, sehen Cloud-Modelle **nur `offen`** - die
Lese-Werkzeuge verweigern alles Strengere.

- **Vererbung:** Symbol, Farbe, Standard-Agents, Layout: der naechste
  gesetzte Wert gewinnt (`null`/fehlend = erben). Ausnahme Symbol bei
  Modulen: eigenes Symbol, sonst das des Typs (man sieht den Typ auf einen
  Blick). **Datenschutz: immer das
  Strengste** aus Bereichskette, eigener Stufe und Mindeststufe des Typs.
  Lockern nach unten ist damit unmoeglich; der Kern verweigert ausserdem das
  Speichern einer Stufe unter der geerbten.
- **Verschieben:** Wird ein Modul/Bereich in einen lockereren Bereich
  verschoben, schreibt der Kern die bisherige Stufe fest (`datenschutz`)
  und dazu `datenschutz_grund` (art, text, datum), z. B. "festgeschrieben
  beim Verschieben aus Unternehmen am 26.09.2026". Die Oberflaeche zeigt
  den Grund an und warnt. In einen strengeren Bereich: die Stufe steigt von
  selbst. Bewusstes Senken ist moeglich bis zur geerbten Stufe; wird dadurch
  irgendetwas lockerer, braucht es eine ausdrueckliche Bestaetigung.
- **Im Zweifel `lokal`:** Kaputte oder unlesbare JSON-Dateien, beide Dateien
  in einem Ordner, fehlendes oder unbekanntes `schema` - der Knoten wird als
  fehlerhaft angezeigt und zaehlt als `lokal` (Kinder erben das).
- **Schreibsperre:** `folder.json`, `module.json` und alles unter `.jarvis\`
  duerfen Werkzeuge (also Agents) nie schreiben - nur der Modul-Dienst im
  Kern. Sonst koennte ein Agent seine eigene Datenschutzstufe senken.

### 5.2 Schema-Versionen

Jede JSON-Datei traegt `"schema": <Zahl>` (derzeit 1).
- **Hoehere Nummer als bekannt:** nicht raten. Knoten = fehlerhaft, zaehlt
  als `lokal`, der Nutzer bekommt eine klare Meldung ("Datei ist neuer als
  dieses Jarvis"). Jarvis **schreibt eine solche Datei nie** (sonst gingen
  Felder der neueren Version verloren).
- **Fehlende oder ungueltige Nummer:** ebenso fehlerhaft und `lokal`.
- **Aeltere Nummer:** wird beim Lesen umgewandelt, sobald es eine gibt
  (Migration im Kern, mit Test).
- Unbekannte Zusatzfelder derselben Version bleiben beim Schreiben erhalten.

### 5.3 Abteilungen und Auftraege (Datenmodell jetzt, Umsetzung Etappe 6)

Ein Modul mit `"abteilung": {"beschreibung", "auftragsarten"}` nimmt
Auftraege an. Ein Auftrag liegt in `.jarvis\auftraege\<id>.json` mit `von`,
`an` (ids), `stufe`, `status`, `auftrag`, `ergebnis`.
**Feste Regel: Daten fliessen nie von einer hoeheren in eine niedrigere
Stufe.** Das Etikett `stufe` eines Auftrags ist das Strengste aller
eingeflossenen Daten; Daten duerfen nur zu Empfaengern mit mindestens dieser
Stufe. Eine Abteilung arbeitet fuer einen strengeren Auftraggeber unter
dessen Regeln und behaelt nichts vom Auftrag bei sich.

## 6. Stand (nach Session 4)

Fertig: **Etappe 0** (Setup), **Etappe 1** (Grundgeruest der Oberflaeche).
**Etappe 2** (Modulsystem) ist gebaut und getestet - gilt als fertig, sobald
der Nutzer sie selbst ausprobiert hat.

- Session 4: erstmals lokal auf Windows; alle Windows-Tests echt bestaetigt
- Modulsystem nach Abschnitt 5: Bereiche, Module, 4 Start-Typen, Vererbung,
  Datenschutzstufen im Kern erzwungen, Schreibsperre fuer Verwaltungsdateien,
  Lese-Werkzeuge zeigen Cloud-Modellen nur `offen`
- Oberflaeche: "+", F2, Strg+X/Strg+V, Ziehen & Ablegen, Eigenschaften mit
  Herkunft und Grund der Stufe, Senken nur mit Bestaetigung
- Echter Workspace eingerichtet: Beispiel, Unternehmen + Trading (vertraulich)
- **432 Tests** (350 Python + 82 Frontend). Nur unter Windows laufen die 5
  Waechter-Tests plus 3 neue (Junction im Baum, Junction nach .jarvis,
  8.3-Kurzname). Der 8.3-Test ueberspringt sich auf D:, weil dort keine
  Kurznamen erzeugt werden (`fsutil 8dot3name query D:` -> deaktiviert) -
  der Umweg existiert dort also nicht. Auf C: (Kurznamen aktiv) wurde er
  am 26.09.2026 einmal mit `--basetemp` auf C: ausgefuehrt: **bestanden**,
  die Sperre erkennt den Kurznamen. Testordner danach geloescht.
- Gearbeitet wird ab Session 4 auf `main`
- **Commit-Nachrichten** unter PowerShell 5.1 ueber eine Datei
  (`git commit -F datei`): Anfuehrungszeichen in `-m "..."` zerlegt
  PowerShell 5.1 beim Weitergeben an git.

Details und naechste Schritte: `ROADMAP.md`.

**Bewusst noch nicht da:** Inhalte der Module (Widgets zeigen noch nichts),
KI in der Oberflaeche, Approval-Gate mit Diff, Logbuch, Kostenzaehler,
Opus-Eskalation, Ollama, echte Agents und Abteilungen, andockbare Panels,
Tauri-Paketierung.

## 7. Befehle (PowerShell)

```powershell
# Einmalig einrichten
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
cd frontend; npm install; cd ..

# Starten
jarvis dev            # Server + Oberflaeche, zeigt den Link mit Token
jarvis serve          # nur der Server
jarvis doctor         # Einrichtung pruefen (kostenlos)

# Pruefen
pytest                            # Python-Tests
cd frontend; npm test; cd ..      # Frontend-Tests
mypy src; ruff check src tests    # Typen und Stil
```
