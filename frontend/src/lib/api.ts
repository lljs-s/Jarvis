/**
 * Der einzige Weg des Frontends zum Server.
 *
 * Wichtig: Das Frontend kennt KEINE API-Keys und KEINE Dateipfade des
 * Rechners. Es kennt nur diese Endpunkte. Jede Anfrage traegt das
 * Sitzungs-Token - ohne das antwortet der Server nicht.
 *
 * Die Typen hier entsprechen genau den Pydantic-Modellen in
 * src/jarvis/server/schemas.py.
 */

import { holeToken } from "./token";

export interface HealthInfo {
  status: "ok";
  version: string;
  etappe: string;
  workspace: string;
  workspace_existiert: boolean;
  modell: string;
  hat_anthropic_key: boolean;
  hat_gemini_key: boolean;
  ki_verbunden: boolean;
}

export interface KostenInfo {
  heute_usd: number;
  heute_eur: number;
  limit_tag_usd: number;
  limit_tag_eur: number;
  limit_aufgabe_usd: number;
  kurs_usd_zu_eur: number;
}

export interface EinstellungenInfo {
  modell: string;
  max_steps: number;
  max_read_bytes: number;
  kosten: KostenInfo;
}

export type AgentStatus = "idle" | "laeuft" | "wartet" | "fertig" | "fehler";

export interface AgentInfo {
  id: string;
  name: string;
  rolle: string;
  modell: string;
  status: AgentStatus;
  max_risiko: "LOW" | "MEDIUM" | "HIGH";
  notiz: string;
}

export type Stufe = "offen" | "vertraulich" | "lokal";

export interface GrundInfo {
  art: string;
  text: string;
  datum: string;
}

/** Ein Bereich oder Modul - mit den wirksamen (vererbten) Werten. */
export interface KnotenInfo {
  id: string;
  art: "bereich" | "modul";
  name: string;
  pfad: string;
  beschreibung: string;
  symbol: string;
  farbe: string;
  datenschutz: Stufe;
  datenschutz_eigen: Stufe | null;
  datenschutz_mindest: Stufe;
  datenschutz_herkunft: string;
  datenschutz_grund: GrundInfo | null;
  typ: string | null;
  typ_name: string | null;
  abteilung: boolean;
  fehler: string | null;
  warnungen: string[];
  kinder: KnotenInfo[];
}

export interface TypInfo {
  id: string;
  name: string;
  beschreibung: string;
  symbol: string;
  mindest_datenschutz: Stufe;
}

export interface AenderungsAntwort {
  baum: KnotenInfo;
  knoten_id: string | null;
  warnungen: string[];
  hinweise: string[];
  braucht_bestaetigung: boolean;
  betroffene: string[];
}

export class ApiFehler extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function pruefe<T>(antwort: Response): Promise<T> {
  if (!antwort.ok) {
    let grund = `Server antwortete mit ${antwort.status}`;
    if (antwort.status === 401) {
      grund =
        "Der Sitzungs-Token fehlt oder ist abgelaufen. Starte Jarvis neu und benutze den angezeigten Link.";
    } else if (antwort.status === 400) {
      // Abgelehnte Aenderung: der Server schickt einen Klartext mit.
      try {
        const daten = (await antwort.json()) as { fehler?: string };
        if (daten.fehler) grund = daten.fehler;
      } catch {
        /* dann bleibt die allgemeine Meldung */
      }
    }
    throw new ApiFehler(grund, antwort.status);
  }
  return (await antwort.json()) as T;
}

async function hole<T>(pfad: string): Promise<T> {
  const antwort = await fetch(pfad, {
    headers: { "X-Jarvis-Token": holeToken() ?? "" },
  });
  return pruefe<T>(antwort);
}

async function sende<T>(pfad: string, daten: object): Promise<T> {
  const antwort = await fetch(pfad, {
    method: "POST",
    headers: { "X-Jarvis-Token": holeToken() ?? "", "Content-Type": "application/json" },
    body: JSON.stringify(daten),
  });
  return pruefe<T>(antwort);
}

export const api = {
  health: () => hole<HealthInfo>("/api/health"),
  einstellungen: () => hole<EinstellungenInfo>("/api/settings"),
  agents: () => hole<AgentInfo[]>("/api/agents"),
  baum: () => hole<KnotenInfo>("/api/modules"),
  typen: () => hole<TypInfo[]>("/api/modules/typen"),
  ordnerAnlegen: (eltern_id: string, name: string) =>
    sende<AenderungsAntwort>("/api/modules/ordner", { eltern_id, name }),
  modulAnlegen: (eltern_id: string, name: string, typ: string) =>
    sende<AenderungsAntwort>("/api/modules/modul", { eltern_id, name, typ }),
  umbenennen: (id: string, name: string) =>
    sende<AenderungsAntwort>("/api/modules/umbenennen", { id, name }),
  verschieben: (id: string, ziel_id: string) =>
    sende<AenderungsAntwort>("/api/modules/verschieben", { id, ziel_id }),
  datenschutzSetzen: (id: string, stufe: Stufe | null, bestaetigt = false) =>
    sende<AenderungsAntwort>("/api/modules/datenschutz", { id, stufe, bestaetigt }),
};
