/**
 * Baukasten fuer Testdaten: vollstaendige KnotenInfo-Objekte mit
 * sinnvollen Standardwerten, damit Tests nur das Wesentliche nennen.
 */

import type { KnotenInfo, TypInfo } from "./lib/api";

export function knoten(teil: Partial<KnotenInfo> & { id: string; name: string }): KnotenInfo {
  return {
    art: "bereich",
    pfad: teil.name,
    beschreibung: "",
    symbol: teil.art === "modul" ? "notizblock" : "ordner",
    farbe: "grau",
    datenschutz: "offen",
    datenschutz_eigen: null,
    datenschutz_mindest: "offen",
    datenschutz_herkunft: "Standard der Wurzel",
    datenschutz_grund: null,
    typ: null,
    typ_name: null,
    abteilung: false,
    fehler: null,
    warnungen: [],
    kinder: [],
    ...teil,
  };
}

export function wurzel(kinder: KnotenInfo[]): KnotenInfo {
  return knoten({ id: "wurzel", name: "Wurzel", pfad: "", kinder });
}

export const TYPEN: TypInfo[] = [
  {
    id: "notizen",
    name: "Notizen",
    beschreibung: "Markdown-Notizen",
    symbol: "notizblock",
    mindest_datenschutz: "offen",
  },
  {
    id: "aufgaben",
    name: "Aufgaben",
    beschreibung: "Aufgabenliste",
    symbol: "haken",
    mindest_datenschutz: "offen",
  },
];
