/**
 * Eine Aenderung am Modulbaum ausfuehren - immer auf dieselbe Art:
 * Server fragen, neuen Baum uebernehmen, Warnungen und Hinweise melden.
 *
 * Alle Pruefungen macht der Server (bzw. der Kern). Die Oberflaeche zeigt
 * nur an, was er sagt - sie entscheidet nie selbst ueber Datenschutz.
 */

import type { AenderungsAntwort } from "../../lib/api";
import { neueId, useStore } from "../../store/store";

/** Meldet Warnungen und Hinweise im Chat, damit sie nicht verloren gehen. */
export function melde(texte: string[], art: "warnung" | "hinweis"): void {
  const zeichen = art === "warnung" ? "⚠️" : "ℹ️";
  for (const text of texte) {
    useStore
      .getState()
      .nachrichtAnhaengen({ id: neueId("sys"), absender: "system", text: `${zeichen} ${text}` });
  }
}

/**
 * Fuehrt den Aufruf aus. Fehler (z. B. "Name schon belegt") wirft er weiter,
 * damit der Aufrufer sie dort anzeigt, wo der Nutzer gerade ist.
 */
export async function aendern(
  aufruf: () => Promise<AenderungsAntwort>,
): Promise<AenderungsAntwort> {
  const antwort = await aufruf();
  if (!antwort.braucht_bestaetigung) {
    useStore.getState().baumSetzen(antwort.baum);
    melde(antwort.warnungen, "warnung");
    melde(antwort.hinweise, "hinweis");
  }
  return antwort;
}

export function fehlertext(fehler: unknown): string {
  return fehler instanceof Error ? fehler.message : String(fehler);
}
