/**
 * Das Jarvis-Chatfeld: der Mittelpunkt der Anwendung.
 *
 * In Etappe 1 antwortet der Server mit einem Platzhalter. Der Weg ist aber
 * schon der echte: Text -> WebSocket -> Antwort in Stuecken -> Anzeige.
 */

import { useEffect, useRef, useState } from "react";
import { Panel } from "../../components/Panel";
import { useStore, neueId } from "../../store/store";
import { hilfetext, vorschlaege, zerlege } from "../../lib/slash";

interface Props {
  senden: (text: string) => boolean;
  eingabeRef: React.RefObject<HTMLTextAreaElement | null>;
}

export function ChatPanel({ senden, eingabeRef }: Props) {
  const [entwurf, setEntwurf] = useState("");
  const nachrichten = useStore((s) => s.nachrichten);
  const verbunden = useStore((s) => s.verbunden);
  const verbindungsfehler = useStore((s) => s.verbindungsfehler);
  const anhaengen = useStore((s) => s.nachrichtAnhaengen);
  const modulWaehlen = useStore((s) => s.modulWaehlen);
  const ende = useRef<HTMLDivElement>(null);

  useEffect(() => {
    ende.current?.scrollIntoView({ block: "end" });
  }, [nachrichten]);

  const hinweise = vorschlaege(entwurf);

  const abschicken = () => {
    const text = entwurf.trim();
    if (!text) return;

    const befehl = zerlege(text);

    // /hilfe beantwortet die Oberflaeche selbst - das kostet nichts und
    // funktioniert auch ohne Server.
    if (befehl.id === "hilfe") {
      anhaengen({ id: neueId("du"), absender: "du", text });
      anhaengen({ id: neueId("sys"), absender: "system", text: hilfetext() });
      setEntwurf("");
      return;
    }

    if (befehl.unbekannt) {
      anhaengen({ id: neueId("du"), absender: "du", text });
      anhaengen({
        id: neueId("sys"),
        absender: "system",
        text: `Den Befehl ${befehl.unbekannt} kenne ich nicht. /hilfe zeigt alle Befehle.`,
      });
      setEntwurf("");
      return;
    }

    if (befehl.id === "modul" && befehl.rest) {
      modulWaehlen(befehl.rest);
    }

    anhaengen({ id: neueId("du"), absender: "du", text });

    if (!senden(text)) {
      anhaengen({
        id: neueId("sys"),
        absender: "system",
        text: "Keine Verbindung zum Jarvis-Server. Laeuft er noch? (Fenster mit 'jarvis dev')",
      });
      setEntwurf("");
      return;
    }

    anhaengen({ id: neueId("jarvis"), absender: "jarvis", text: "", laeuft: true });
    setEntwurf("");
  };

  return (
    <Panel
      titel="Jarvis"
      werkzeuge={
        <span
          className="flex items-center gap-2 text-xs text-[var(--color-text-leise)]"
          role="status"
        >
          <span
            aria-hidden
            className={`inline-block h-2 w-2 rounded-full ${verbunden ? "bg-green-500" : "bg-yellow-500"}`}
          />
          {verbunden ? "verbunden" : (verbindungsfehler ?? "verbinde …")}
        </span>
      }
      className="flex-1 border-x"
    >
      <div className="flex h-full flex-col">
        <div className="min-h-0 flex-1 space-y-4 overflow-auto p-4" aria-live="polite">
          {nachrichten.length === 0 && (
            <div className="mx-auto max-w-lg pt-10 text-center text-[var(--color-text-leise)]">
              <p className="text-base">Hallo. Ich bin Jarvis.</p>
              <p className="mt-2 text-sm">
                Ich bin noch nicht an ein Modell angeschlossen - das kommt in Etappe 3.
                Probier solange <kbd className="rounded border border-[var(--color-rand)] px-1">Strg+K</kbd>{" "}
                fuer die Befehlspalette oder schreib <span className="font-mono">/hilfe</span>.
              </p>
            </div>
          )}

          {nachrichten.map((nachricht) => (
            <article key={nachricht.id} className="flex gap-3">
              <span
                className={`mt-0.5 shrink-0 rounded px-2 py-0.5 text-[11px] font-semibold ${
                  nachricht.absender === "du"
                    ? "bg-[var(--color-akzent-leise)] text-[var(--color-akzent)]"
                    : nachricht.absender === "system"
                      ? "bg-[var(--color-flaeche-2)] text-[var(--color-text-leise)]"
                      : "bg-[var(--color-flaeche-2)] text-[var(--color-text)]"
                }`}
              >
                {nachricht.absender === "du" ? "Du" : nachricht.absender === "system" ? "System" : "Jarvis"}
              </span>
              <p className="whitespace-pre-wrap leading-relaxed">
                {nachricht.text}
                {nachricht.laeuft && <span className="animate-pulse"> ▍</span>}
              </p>
            </article>
          ))}
          <div ref={ende} />
        </div>

        {hinweise.length > 0 && (
          <ul className="border-t border-[var(--color-rand)] bg-[var(--color-flaeche-2)] px-4 py-2 text-xs">
            {hinweise.map((b) => (
              <li key={b.id} className="py-0.5">
                <span className="font-mono text-[var(--color-akzent)]">{b.name}</span>
                <span className="ml-2 text-[var(--color-text-leise)]">{b.kurz}</span>
              </li>
            ))}
          </ul>
        )}

        <div className="shrink-0 border-t border-[var(--color-rand)] p-3">
          <label htmlFor="chat-eingabe" className="sr-only">
            Nachricht an Jarvis
          </label>
          <textarea
            id="chat-eingabe"
            ref={eingabeRef}
            rows={2}
            value={entwurf}
            onChange={(e) => setEntwurf(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                abschicken();
              }
            }}
            placeholder="Nachricht an Jarvis …  (Enter sendet, Shift+Enter macht eine neue Zeile)"
            className="w-full resize-none rounded border border-[var(--color-rand)] bg-[var(--color-flaeche-2)] px-3 py-2 outline-none focus:border-[var(--color-akzent)]"
          />
          <div className="mt-2 flex items-center justify-between text-xs text-[var(--color-text-leise)]">
            <span>Strg+J springt hierher · /hilfe zeigt alle Befehle</span>
            <button
              type="button"
              onClick={abschicken}
              className="rounded bg-[var(--color-akzent)] px-3 py-1 font-medium text-white disabled:opacity-40"
              disabled={!entwurf.trim()}
            >
              Senden
            </button>
          </div>
        </div>
      </div>
    </Panel>
  );
}
