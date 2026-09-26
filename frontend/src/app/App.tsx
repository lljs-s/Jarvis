/**
 * Das Hauptfenster.
 *
 * Aufbau (Etappe 1 noch fest, ab Etappe 7 verschiebbare Panels):
 *
 *   +------------------------------------------------------+
 *   | Kopfzeile: Titel, Befehlspalette, Thema, Einstellungen|
 *   +---------+------------------------------+-------------+
 *   | Module  |  Jarvis (Chat)               | Agents      |
 *   +---------+------------------------------+-------------+
 *   | Statusleiste: Workspace, Kosten, Modell, Version      |
 *   +------------------------------------------------------+
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Sidebar } from "../features/modules/Sidebar";
import { ChatPanel } from "../features/chat/ChatPanel";
import { AgentsPanel } from "../features/agents/AgentsPanel";
import { SettingsDialog } from "../features/settings/SettingsDialog";
import { CommandPalette } from "../components/CommandPalette";
import { StatusBar } from "../components/StatusBar";
import { useStore, neueId } from "../store/store";
import { findeAktion, alsText, type AktionsId } from "../lib/shortcuts";
import { hilfetext } from "../lib/slash";
import { api, type EinstellungenInfo, type HealthInfo } from "../lib/api";
import { ChatVerbindung } from "../lib/chatVerbindung";

export function App() {
  const thema = useStore((s) => s.thema);
  const belegung = useStore((s) => s.belegung);
  const seitenleisteSichtbar = useStore((s) => s.seitenleisteSichtbar);
  const agentsSichtbar = useStore((s) => s.agentsSichtbar);
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const [einstellungen, setEinstellungen] = useState<EinstellungenInfo | null>(null);
  const [startfehler, setStartfehler] = useState<string | null>(null);

  const eingabeRef = useRef<HTMLTextAreaElement>(null);
  const verbindung = useRef<ChatVerbindung | null>(null);

  // Hell/Dunkel am <html>-Element, damit auch der Hintergrund stimmt.
  useEffect(() => {
    document.documentElement.classList.toggle("dunkel", thema === "dunkel");
  }, [thema]);

  // Daten vom Server holen.
  useEffect(() => {
    const laden = async () => {
      try {
        const [gesundheit, werte, agents, baum, typen] = await Promise.all([
          api.health(),
          api.einstellungen(),
          api.agents(),
          api.baum(),
          api.typen(),
        ]);
        setHealth(gesundheit);
        setEinstellungen(werte);
        useStore.getState().agentsSetzen(agents);
        useStore.getState().baumSetzen(baum);
        useStore.getState().typenSetzen(typen);
        setStartfehler(null);
      } catch (fehler) {
        setStartfehler(fehler instanceof Error ? fehler.message : String(fehler));
      }
    };
    void laden();
  }, []);

  // Chat-Verbindung aufbauen.
  useEffect(() => {
    const store = useStore.getState();
    const verb = new ChatVerbindung({
      aufVerbindung: (verbunden, grund) => store.verbindungSetzen(verbunden, grund),
      aufEreignis: (ereignis) => {
        const s = useStore.getState();
        if (ereignis.typ === "stueck") s.anLetzteAnhaengen(ereignis.text);
        if (ereignis.typ === "ende") s.letzteAbschliessen();
        if (ereignis.typ === "fehler") {
          s.letzteAbschliessen();
          s.nachrichtAnhaengen({ id: neueId("sys"), absender: "system", text: ereignis.text });
        }
      },
    });
    verb.verbinde();
    verbindung.current = verb;
    return () => verb.schliesse();
  }, []);

  const aktionAusfuehren = useCallback((id: string) => {
    const store = useStore.getState();

    if (id.startsWith("modul:")) {
      store.modulWaehlen(id.slice("modul:".length));
      return;
    }
    if (id.startsWith("agent:") || id.startsWith("slash:")) {
      const wert = id.slice(id.indexOf(":") + 1);
      store.nachrichtAnhaengen({
        id: neueId("sys"),
        absender: "system",
        text: id.startsWith("agent:")
          ? `Agents starten kommt in Etappe 6 (gewaehlt: ${wert}).`
          : `Tippe ${wert} direkt ins Chatfeld - Strg+J bringt dich hin.`,
      });
      return;
    }

    switch (id as AktionsId) {
      case "befehlspalette":
        store.paletteSetzen(true);
        break;
      case "chatFokus":
        eingabeRef.current?.focus();
        break;
      case "seitenleisteUmschalten":
        store.seitenleisteUmschalten();
        break;
      case "agentsUmschalten":
        store.agentsUmschalten();
        break;
      case "themaWechseln":
        store.themaWechseln();
        break;
      case "einstellungen":
        store.einstellungenSetzen(true);
        break;
      case "hilfe":
        store.nachrichtAnhaengen({ id: neueId("sys"), absender: "system", text: hilfetext() });
        break;
    }
  }, []);

  // Eine einzige Stelle fuer alle Tastenkuerzel.
  useEffect(() => {
    const beiTaste = (e: KeyboardEvent) => {
      const aktion = findeAktion(e, belegung);
      if (!aktion) return;
      e.preventDefault();
      aktionAusfuehren(aktion);
    };
    window.addEventListener("keydown", beiTaste);
    return () => window.removeEventListener("keydown", beiTaste);
  }, [belegung, aktionAusfuehren]);

  const senden = useCallback((text: string) => verbindung.current?.sende(text) ?? false, []);

  return (
    <div className="flex h-full flex-col bg-[var(--color-flaeche)] text-[var(--color-text)]">
      <header className="flex shrink-0 items-center justify-between gap-3 border-b border-[var(--color-rand)] px-3 py-2">
        <div className="flex items-center gap-2">
          <span className="text-base font-semibold">Jarvis</span>
          <span className="text-xs text-[var(--color-text-leise)]">{health?.etappe ?? ""}</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => useStore.getState().paletteSetzen(true)}
            className="rounded border border-[var(--color-rand)] px-2 py-1 text-xs hover:bg-[var(--color-flaeche-2)]"
          >
            Befehle <kbd className="ml-1 opacity-70">{alsText(belegung.befehlspalette)}</kbd>
          </button>
          <button
            type="button"
            onClick={() => useStore.getState().themaWechseln()}
            aria-label="Hell- oder Dunkelmodus umschalten"
            className="rounded border border-[var(--color-rand)] px-2 py-1 text-xs hover:bg-[var(--color-flaeche-2)]"
          >
            {thema === "hell" ? "🌙 dunkel" : "☀ hell"}
          </button>
          <button
            type="button"
            onClick={() => useStore.getState().einstellungenSetzen(true)}
            aria-label="Einstellungen oeffnen"
            className="rounded border border-[var(--color-rand)] px-2 py-1 text-xs hover:bg-[var(--color-flaeche-2)]"
          >
            Einstellungen
          </button>
        </div>
      </header>

      {startfehler && (
        <div
          role="alert"
          className="shrink-0 border-b border-[var(--color-rand)] bg-yellow-100 px-3 py-2 text-sm text-yellow-900"
        >
          {startfehler}
        </div>
      )}

      <main className="flex min-h-0 flex-1">
        {seitenleisteSichtbar && <Sidebar />}
        <ChatPanel senden={senden} eingabeRef={eingabeRef} />
        {agentsSichtbar && <AgentsPanel />}
      </main>

      <StatusBar health={health} einstellungen={einstellungen} />

      <CommandPalette aktionAusfuehren={aktionAusfuehren} />
      <SettingsDialog einstellungen={einstellungen} />
    </div>
  );
}
