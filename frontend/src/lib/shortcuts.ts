/**
 * Tastenkuerzel - Daten statt fest verdrahteter if-Abfragen.
 *
 * Jede Aktion hat einen Namen, eine Beschreibung und eine Tastenkombination.
 * Der Nutzer kann die Kombination in den Einstellungen aendern; gespeichert
 * wird sie im Browser (localStorage). Die Pruefung selbst ist eine reine
 * Funktion - deshalb laesst sie sich ohne Oberflaeche testen.
 */

export type AktionsId =
  | "befehlspalette"
  | "chatFokus"
  | "themaWechseln"
  | "seitenleisteUmschalten"
  | "agentsUmschalten"
  | "einstellungen"
  | "hilfe";

export interface Tastenkombination {
  taste: string; // z. B. "k", "Enter", "/"
  strg?: boolean;
  shift?: boolean;
  alt?: boolean;
}

export interface Aktion {
  id: AktionsId;
  titel: string;
  beschreibung: string;
  standard: Tastenkombination;
}

export const AKTIONEN: Aktion[] = [
  {
    id: "befehlspalette",
    titel: "Befehlspalette oeffnen",
    beschreibung: "Module oeffnen, Agents starten, Einstellungen - alles ueber eine Liste.",
    standard: { taste: "k", strg: true },
  },
  {
    id: "chatFokus",
    titel: "Zum Jarvis-Chatfeld springen",
    beschreibung: "Setzt den Schreibcursor ins Eingabefeld, egal wo du gerade bist.",
    standard: { taste: "j", strg: true },
  },
  {
    id: "seitenleisteUmschalten",
    titel: "Seitenleiste ein-/ausblenden",
    beschreibung: "Mehr Platz fuer den Chat.",
    standard: { taste: "b", strg: true },
  },
  {
    id: "agentsUmschalten",
    titel: "Agents-Tab ein-/ausblenden",
    beschreibung: "Blendet die Agent-Liste rechts aus.",
    standard: { taste: "e", strg: true },
  },
  {
    id: "themaWechseln",
    titel: "Hell/Dunkel wechseln",
    beschreibung: "Schaltet zwischen hellem und dunklem Erscheinungsbild.",
    standard: { taste: "l", strg: true, shift: true },
  },
  {
    id: "einstellungen",
    titel: "Einstellungen oeffnen",
    beschreibung: "Tastenkuerzel, Modelle, Kosten.",
    standard: { taste: ",", strg: true },
  },
  {
    id: "hilfe",
    titel: "Hilfe anzeigen",
    beschreibung: "Zeigt alle Tastenkuerzel und Slash-Befehle.",
    standard: { taste: "F1" },
  },
];

export type Tastenbelegung = Record<AktionsId, Tastenkombination>;

export function standardBelegung(): Tastenbelegung {
  const belegung = {} as Tastenbelegung;
  for (const aktion of AKTIONEN) belegung[aktion.id] = aktion.standard;
  return belegung;
}

/**
 * Passt ein Tastendruck-Ereignis zu einer Kombination?
 *
 * Auf dem Mac ist Strg die Befehlstaste - wir akzeptieren beide, damit das
 * Projekt spaeter ohne Aenderung auch dort laeuft.
 */
export function passt(
  ereignis: Pick<KeyboardEvent, "key" | "ctrlKey" | "metaKey" | "shiftKey" | "altKey">,
  kombination: Tastenkombination,
): boolean {
  const strgGedrueckt = ereignis.ctrlKey || ereignis.metaKey;
  if (Boolean(kombination.strg) !== strgGedrueckt) return false;
  if (Boolean(kombination.shift) !== ereignis.shiftKey) return false;
  if (Boolean(kombination.alt) !== ereignis.altKey) return false;
  return ereignis.key.toLowerCase() === kombination.taste.toLowerCase();
}

/** Findet die Aktion zu einem Tastendruck - oder undefined. */
export function findeAktion(
  ereignis: Pick<KeyboardEvent, "key" | "ctrlKey" | "metaKey" | "shiftKey" | "altKey">,
  belegung: Tastenbelegung,
): AktionsId | undefined {
  for (const aktion of AKTIONEN) {
    const kombination = belegung[aktion.id];
    if (kombination && passt(ereignis, kombination)) return aktion.id;
  }
  return undefined;
}

/** Schreibweise fuer die Anzeige: { taste: "k", strg: true } -> "Strg+K" */
export function alsText(kombination: Tastenkombination): string {
  const teile: string[] = [];
  if (kombination.strg) teile.push("Strg");
  if (kombination.shift) teile.push("Shift");
  if (kombination.alt) teile.push("Alt");
  const taste = kombination.taste.length === 1
    ? kombination.taste.toUpperCase()
    : kombination.taste;
  teile.push(taste);
  return teile.join("+");
}

/** Liest einen Tastendruck als neue Kombination (fuer den Einstellungsdialog). */
export function ausEreignis(ereignis: KeyboardEvent): Tastenkombination | undefined {
  const reineModifikatoren = ["Control", "Shift", "Alt", "Meta"];
  if (reineModifikatoren.includes(ereignis.key)) return undefined;
  return {
    taste: ereignis.key,
    strg: ereignis.ctrlKey || ereignis.metaKey,
    shift: ereignis.shiftKey,
    alt: ereignis.altKey,
  };
}

const SPEICHER_SCHLUESSEL = "jarvis.tastenbelegung";

export function ladeBelegung(): Tastenbelegung {
  const standard = standardBelegung();
  try {
    const gespeichert = localStorage.getItem(SPEICHER_SCHLUESSEL);
    if (!gespeichert) return standard;
    const gelesen = JSON.parse(gespeichert) as Partial<Tastenbelegung>;
    return { ...standard, ...gelesen };
  } catch {
    // Kaputter oder gesperrter Speicher darf die App nicht aufhalten.
    return standard;
  }
}

export function speichereBelegung(belegung: Tastenbelegung): void {
  try {
    localStorage.setItem(SPEICHER_SCHLUESSEL, JSON.stringify(belegung));
  } catch {
    /* nicht schlimm - dann gelten beim naechsten Start wieder die Standards */
  }
}
