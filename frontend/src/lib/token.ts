/**
 * Das Sitzungs-Token.
 *
 * Es steht beim ersten Aufruf in der Adresse (?token=...). Wir merken es
 * uns im sessionStorage und raeumen die Adresszeile sofort auf - so steht
 * das Geheimnis nicht im Browserverlauf und nicht in Screenshots.
 *
 * sessionStorage (nicht localStorage): das Token gilt ohnehin nur, bis der
 * Server neu startet.
 */

const SCHLUESSEL = "jarvis.token";

export function uebernehmeTokenAusAdresse(ort: Location = window.location): void {
  const adresse = new URL(ort.href);
  const token = adresse.searchParams.get("token");
  if (!token) return;
  try {
    sessionStorage.setItem(SCHLUESSEL, token);
  } catch {
    /* Privater Modus: dann gilt das Token nur fuer diese Seite */
  }
  adresse.searchParams.delete("token");
  window.history.replaceState({}, "", adresse.pathname + adresse.search + adresse.hash);
}

export function holeToken(): string | null {
  try {
    return sessionStorage.getItem(SCHLUESSEL);
  } catch {
    return null;
  }
}

/** Adresse des Chat-WebSockets, inklusive Token. */
export function chatAdresse(ort: Location = window.location): string {
  const protokoll = ort.protocol === "https:" ? "wss:" : "ws:";
  return `${protokoll}//${ort.host}/ws/chat?token=${encodeURIComponent(holeToken() ?? "")}`;
}
