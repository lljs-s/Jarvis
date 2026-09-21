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

export interface ModulInfo {
  id: string;
  name: string;
  symbol: string;
  typ: "ordner" | "modul";
  kinder: ModulInfo[];
}

export class ApiFehler extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function hole<T>(pfad: string): Promise<T> {
  const antwort = await fetch(pfad, {
    headers: { "X-Jarvis-Token": holeToken() ?? "" },
  });
  if (!antwort.ok) {
    const grund =
      antwort.status === 401
        ? "Der Sitzungs-Token fehlt oder ist abgelaufen. Starte Jarvis neu und benutze den angezeigten Link."
        : `Server antwortete mit ${antwort.status}`;
    throw new ApiFehler(grund, antwort.status);
  }
  return (await antwort.json()) as T;
}

export const api = {
  health: () => hole<HealthInfo>("/api/health"),
  einstellungen: () => hole<EinstellungenInfo>("/api/settings"),
  agents: () => hole<AgentInfo[]>("/api/agents"),
  module: () => hole<ModulInfo[]>("/api/modules"),
};
