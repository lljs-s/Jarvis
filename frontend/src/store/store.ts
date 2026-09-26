/**
 * Der Zustand der Oberflaeche an einer Stelle.
 *
 * zustand statt Redux: ein Store ist eine Funktion, kein Baukasten aus
 * Actions, Reducern und Middleware. Fuer eine App dieser Groesse ist das
 * genau richtig.
 */

import { create } from "zustand";
import type { AgentInfo, KnotenInfo } from "../lib/api";
import {
  ladeBelegung,
  speichereBelegung,
  standardBelegung,
  type AktionsId,
  type Tastenbelegung,
  type Tastenkombination,
} from "../lib/shortcuts";

export type Thema = "hell" | "dunkel";

export interface ChatNachricht {
  id: string;
  absender: "du" | "jarvis" | "system";
  text: string;
  laeuft?: boolean;
}

interface Zustand {
  // Aussehen
  thema: Thema;
  themaSetzen: (thema: Thema) => void;
  themaWechseln: () => void;

  // Panels
  seitenleisteSichtbar: boolean;
  agentsSichtbar: boolean;
  seitenleisteUmschalten: () => void;
  agentsUmschalten: () => void;

  // Dialoge
  paletteOffen: boolean;
  einstellungenOffen: boolean;
  paletteSetzen: (offen: boolean) => void;
  einstellungenSetzen: (offen: boolean) => void;

  // Inhalte
  nachrichten: ChatNachricht[];
  nachrichtAnhaengen: (nachricht: ChatNachricht) => void;
  anLetzteAnhaengen: (text: string) => void;
  letzteAbschliessen: () => void;
  chatLeeren: () => void;

  agents: AgentInfo[];
  agentsSetzen: (agents: AgentInfo[]) => void;
  /** Die Wurzel des Modulbaums; `module` sind ihre Kinder (die oberste Ebene). */
  wurzel: KnotenInfo | null;
  module: KnotenInfo[];
  baumSetzen: (wurzel: KnotenInfo) => void;
  gewaehltesModul: string | null;
  modulWaehlen: (id: string | null) => void;

  // Verbindung
  verbunden: boolean;
  verbindungsfehler: string | null;
  verbindungSetzen: (verbunden: boolean, fehler?: string) => void;

  // Tastenkuerzel
  belegung: Tastenbelegung;
  belegungSetzen: (id: AktionsId, kombination: Tastenkombination) => void;
  belegungZuruecksetzen: () => void;
}

function themaAusSpeicher(): Thema {
  try {
    const gespeichert = localStorage.getItem("jarvis.thema");
    if (gespeichert === "hell" || gespeichert === "dunkel") return gespeichert;
  } catch {
    /* egal */
  }
  const dunkelBevorzugt =
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-color-scheme: dark)").matches;
  return dunkelBevorzugt ? "dunkel" : "hell";
}

let zaehler = 0;
export function neueId(praefix = "n"): string {
  zaehler += 1;
  return `${praefix}-${zaehler}`;
}

export const useStore = create<Zustand>((set) => ({
  thema: themaAusSpeicher(),
  themaSetzen: (thema) => {
    try {
      localStorage.setItem("jarvis.thema", thema);
    } catch {
      /* egal */
    }
    set({ thema });
  },
  themaWechseln: () =>
    set((s) => {
      const neu: Thema = s.thema === "hell" ? "dunkel" : "hell";
      try {
        localStorage.setItem("jarvis.thema", neu);
      } catch {
        /* egal */
      }
      return { thema: neu };
    }),

  seitenleisteSichtbar: true,
  agentsSichtbar: true,
  seitenleisteUmschalten: () => set((s) => ({ seitenleisteSichtbar: !s.seitenleisteSichtbar })),
  agentsUmschalten: () => set((s) => ({ agentsSichtbar: !s.agentsSichtbar })),

  paletteOffen: false,
  einstellungenOffen: false,
  paletteSetzen: (offen) => set({ paletteOffen: offen }),
  einstellungenSetzen: (offen) => set({ einstellungenOffen: offen }),

  nachrichten: [],
  nachrichtAnhaengen: (nachricht) => set((s) => ({ nachrichten: [...s.nachrichten, nachricht] })),
  anLetzteAnhaengen: (text) =>
    set((s) => {
      const nachrichten = [...s.nachrichten];
      const letzte = nachrichten[nachrichten.length - 1];
      if (!letzte) return {};
      nachrichten[nachrichten.length - 1] = { ...letzte, text: letzte.text + text };
      return { nachrichten };
    }),
  letzteAbschliessen: () =>
    set((s) => {
      const nachrichten = [...s.nachrichten];
      const letzte = nachrichten[nachrichten.length - 1];
      if (!letzte) return {};
      nachrichten[nachrichten.length - 1] = { ...letzte, laeuft: false };
      return { nachrichten };
    }),
  chatLeeren: () => set({ nachrichten: [] }),

  agents: [],
  agentsSetzen: (agents) => set({ agents }),
  wurzel: null,
  module: [],
  baumSetzen: (wurzel) => set({ wurzel, module: wurzel.kinder }),
  gewaehltesModul: null,
  modulWaehlen: (id) => set({ gewaehltesModul: id }),

  verbunden: false,
  verbindungsfehler: null,
  verbindungSetzen: (verbunden, fehler) =>
    set({ verbunden, verbindungsfehler: fehler ?? null }),

  belegung: ladeBelegung(),
  belegungSetzen: (id, kombination) =>
    set((s) => {
      const belegung = { ...s.belegung, [id]: kombination };
      speichereBelegung(belegung);
      return { belegung };
    }),
  belegungZuruecksetzen: () => {
    const belegung = standardBelegung();
    speichereBelegung(belegung);
    set({ belegung });
  },
}));
