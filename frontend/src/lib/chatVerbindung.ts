/**
 * Die WebSocket-Verbindung zum Chat.
 *
 * Gekapselt, damit die Oberflaeche nur "verbinde", "sende" und "getrennt"
 * kennt - und damit in Etappe 3 nur hier etwas passiert, wenn statt des
 * Platzhalters ein echtes Modell antwortet.
 */

import { chatAdresse } from "./token";

export interface ChatEreignis {
  typ: "start" | "stueck" | "ende" | "fehler" | "hinweis";
  text: string;
  absender: "jarvis" | "system";
}

export interface ChatRueckrufe {
  aufEreignis: (ereignis: ChatEreignis) => void;
  aufVerbindung: (verbunden: boolean, grund?: string) => void;
}

/** Erklaert die Schliesscodes des Servers in verstaendlichem Deutsch. */
export function grundZuText(code: number): string {
  if (code === 4401) {
    return "Sitzungs-Token fehlt oder ist falsch. Bitte Jarvis neu starten und den angezeigten Link benutzen.";
  }
  if (code === 4403) {
    return "Diese Herkunft ist nicht erlaubt. Oeffne Jarvis ueber den angezeigten Link (127.0.0.1).";
  }
  if (code === 1000 || code === 1001) return "Verbindung beendet.";
  return `Verbindung getrennt (Code ${code}).`;
}

export class ChatVerbindung {
  private socket: WebSocket | null = null;

  constructor(private readonly rueckrufe: ChatRueckrufe) {}

  verbinde(): void {
    this.socket = new WebSocket(chatAdresse());
    this.socket.onopen = () => this.rueckrufe.aufVerbindung(true);
    this.socket.onmessage = (nachricht) => {
      try {
        this.rueckrufe.aufEreignis(JSON.parse(nachricht.data as string) as ChatEreignis);
      } catch {
        /* unverstaendliche Nachricht ignorieren */
      }
    };
    this.socket.onclose = (ereignis) =>
      this.rueckrufe.aufVerbindung(false, grundZuText(ereignis.code));
    this.socket.onerror = () => this.rueckrufe.aufVerbindung(false, "Server nicht erreichbar.");
  }

  sende(text: string): boolean {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return false;
    this.socket.send(JSON.stringify({ typ: "nachricht", text }));
    return true;
  }

  schliesse(): void {
    this.socket?.close();
    this.socket = null;
  }
}
