/**
 * Reine Hilfsfunktionen fuer den Modulbaum - ohne React, dadurch leicht testbar.
 */

import type { KnotenInfo, Stufe } from "../../lib/api";

/** Symbolnamen aus den JSON-Dateien -> Zeichen fuer die Anzeige. */
const SYMBOLE: Record<string, string> = {
  ordner: "📁",
  modul: "📄",
  stern: "⭐",
  buch: "📘",
  notizblock: "📝",
  lupe: "🔎",
  haken: "✅",
  ablage: "🗂️",
  herz: "❤️",
};

export function symbolZeichen(symbol: string): string {
  return SYMBOLE[symbol] ?? "📄";
}

/** Farbnamen (siehe FARBEN in formate.py) -> CSS-Farbe fuer den Punkt. */
const FARBEN: Record<string, string> = {
  grau: "#9ca3af",
  rot: "#ef4444",
  orange: "#f97316",
  gelb: "#eab308",
  gruen: "#22c55e",
  blau: "#3b82f6",
  lila: "#a855f7",
  pink: "#ec4899",
};

export function farbWert(farbe: string): string {
  return FARBEN[farbe] ?? FARBEN.grau!;
}

export const STUFEN: Stufe[] = ["offen", "vertraulich", "lokal"];

export const STUFEN_TEXT: Record<Stufe, { name: string; kurz: string; erklaerung: string }> = {
  offen: { name: "Offen", kurz: "", erklaerung: "Alle Modelle dürfen die Daten sehen, auch Cloud." },
  vertraulich: {
    name: "Vertraulich",
    kurz: "🔒",
    erklaerung: "Cloud-Modelle nur nach deiner Freigabe pro Aufgabe.",
  },
  lokal: {
    name: "Lokal",
    kurz: "🏠",
    erklaerung: "Nur lokale Modelle (Ollama) – solange es keins gibt: gar kein Modell.",
  },
};

export function rang(stufe: Stufe): number {
  return STUFEN.indexOf(stufe);
}

/** Welche Stufen darf man hier einstellen? Nie tiefer als die geerbte. */
export function waehlbareStufen(knoten: KnotenInfo): Stufe[] {
  return STUFEN.filter((s) => rang(s) >= rang(knoten.datenschutz_mindest));
}

export function finde(wurzel: KnotenInfo | null, id: string | null): KnotenInfo | null {
  if (!wurzel || !id) return null;
  if (wurzel.id === id) return wurzel;
  for (const kind of wurzel.kinder) {
    const treffer = finde(kind, id);
    if (treffer) return treffer;
  }
  return null;
}

export function eltern(wurzel: KnotenInfo | null, id: string): KnotenInfo | null {
  if (!wurzel) return null;
  for (const kind of wurzel.kinder) {
    if (kind.id === id) return wurzel;
    const treffer = eltern(kind, id);
    if (treffer) return treffer;
  }
  return null;
}

/**
 * Wohin kommt etwas Neues? In den gewaehlten Bereich - ist ein Modul gewaehlt,
 * in dessen Bereich. Sonst in die Wurzel.
 */
export function zielBereich(wurzel: KnotenInfo | null, gewaehlt: string | null): KnotenInfo | null {
  const knoten = finde(wurzel, gewaehlt);
  if (!knoten) return wurzel;
  if (knoten.art === "bereich" && !knoten.fehler) return knoten;
  return eltern(wurzel, knoten.id) ?? wurzel;
}

/** Alle Bereichs-ids bis zur angegebenen Tiefe - zum Aufklappen beim Start. */
export function bereicheBisTiefe(knoten: KnotenInfo[], tiefe: number): string[] {
  if (tiefe <= 0) return [];
  return knoten
    .filter((k) => k.art === "bereich")
    .flatMap((k) => [k.id, ...bereicheBisTiefe(k.kinder, tiefe - 1)]);
}
