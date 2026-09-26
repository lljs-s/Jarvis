/**
 * Slash-Befehle im Chat: "/opus Analysiere ..." statt Maus.
 *
 * Die Zerlegung ist eine reine Funktion - dadurch testbar, ohne den Chat
 * zu oeffnen. Was ein Befehl TUT, entscheidet die Oberflaeche.
 */

export type BefehlsId = "opus" | "agent" | "modul" | "hilfe";

export interface Slashbefehl {
  id: BefehlsId;
  name: string;
  kurz: string;
  beispiel: string;
}

export const SLASHBEFEHLE: Slashbefehl[] = [
  {
    id: "opus",
    name: "/opus",
    kurz: "Aufgabe direkt an den Thinktank (Claude Opus) geben",
    beispiel: "/opus Vergleiche diese zwei Loesungswege und sag mir, welcher robuster ist.",
  },
  {
    id: "agent",
    name: "/agent",
    kurz: "Agent anlegen, starten oder anzeigen",
    beispiel: "/agent recherche Suche mir Quellen zum Referat",
  },
  {
    id: "modul",
    name: "/modul",
    kurz: "Modul oeffnen oder anlegen",
    beispiel: "/modul Schule/Mathe",
  },
  {
    id: "hilfe",
    name: "/hilfe",
    kurz: "Alle Befehle und Tastenkuerzel anzeigen",
    beispiel: "/hilfe",
  },
];

export interface ZerlegterBefehl {
  istBefehl: boolean;
  id?: BefehlsId;
  name?: string;
  rest: string;
  unbekannt?: string;
}

export function zerlege(eingabe: string): ZerlegterBefehl {
  const text = eingabe.trimStart();
  if (!text.startsWith("/")) return { istBefehl: false, rest: eingabe };

  const leerzeichen = text.indexOf(" ");
  const name = (leerzeichen === -1 ? text : text.slice(0, leerzeichen)).toLowerCase();
  const rest = leerzeichen === -1 ? "" : text.slice(leerzeichen + 1).trim();

  const treffer = SLASHBEFEHLE.find((b) => b.name === name);
  if (!treffer) return { istBefehl: true, rest, unbekannt: name };
  return { istBefehl: true, id: treffer.id, name: treffer.name, rest };
}

/** Vorschlaege waehrend des Tippens: "/o" -> [/opus] */
export function vorschlaege(eingabe: string): Slashbefehl[] {
  const text = eingabe.trimStart();
  if (!text.startsWith("/")) return [];
  if (text.includes(" ")) return [];
  return SLASHBEFEHLE.filter((b) => b.name.startsWith(text.toLowerCase()));
}

export function hilfetext(): string {
  const zeilen = SLASHBEFEHLE.map((b) => `${b.name.padEnd(8)} ${b.kurz}`);
  return [
    "Slash-Befehle im Chat:",
    ...zeilen,
    "",
    "Tastenkuerzel: Strg+K Befehlspalette, Strg+J hierher springen,",
    "Strg+B Seitenleiste, Strg+E Agents, Strg+, Einstellungen, F1 Hilfe.",
    "Alle Kuerzel sind in den Einstellungen aenderbar.",
    "",
    "Im Modulbaum: + legt Ordner oder Module an, F2 benennt um,",
    "Strg+X und dann Strg+V auf einem Bereich verschiebt (oder mit der Maus ziehen).",
  ].join("\n");
}
