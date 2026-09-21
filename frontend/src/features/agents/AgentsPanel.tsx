/**
 * Der Agents-Tab, direkt am Jarvis-Bereich angedockt.
 *
 * Etappe 1 zeigt die drei Vorlagen aus dem Server. "+" und "x" sind schon
 * da und erklaeren, was spaeter passiert - Loeschen fragt bereits nach.
 */

import { useState } from "react";
import { Panel } from "../../components/Panel";
import { useStore, neueId } from "../../store/store";
import type { AgentStatus } from "../../lib/api";

const STATUS_TEXT: Record<AgentStatus, string> = {
  idle: "bereit",
  laeuft: "laeuft",
  wartet: "wartet auf Freigabe",
  fertig: "fertig",
  fehler: "Fehler",
};

const STATUS_FARBE: Record<AgentStatus, string> = {
  idle: "bg-gray-400",
  laeuft: "bg-blue-500 animate-pulse",
  wartet: "bg-yellow-500",
  fertig: "bg-green-500",
  fehler: "bg-red-500",
};

export function AgentsPanel() {
  const agents = useStore((s) => s.agents);
  const agentsSetzen = useStore((s) => s.agentsSetzen);
  const anhaengen = useStore((s) => s.nachrichtAnhaengen);
  const [loeschKandidat, setLoeschKandidat] = useState<string | null>(null);

  const anlegen = () => {
    anhaengen({
      id: neueId("sys"),
      absender: "system",
      text:
        "Agents anlegen kommt in Etappe 6. Dann fuehrt dich hier ein kurzer Dialog " +
        "durch Name, Rolle, Modell, erlaubte Werkzeuge, erlaubte Module und die " +
        "hoechste Risikostufe ohne Rueckfrage - und legt daraus eine agent.yaml an.",
    });
  };

  return (
    <Panel
      titel="Agents"
      kuerzel="Strg+E"
      werkzeuge={
        <button
          type="button"
          onClick={anlegen}
          aria-label="Neuen Agent anlegen"
          title="Neuen Agent anlegen"
          className="rounded border border-[var(--color-rand)] px-2 py-0.5 text-sm hover:bg-[var(--color-flaeche-2)]"
        >
          +
        </button>
      }
      className="w-72 shrink-0"
    >
      <ul className="divide-y divide-[var(--color-rand)]">
        {agents.map((agent) => (
          <li key={agent.id} className="p-3">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span
                    aria-hidden
                    className={`inline-block h-2 w-2 shrink-0 rounded-full ${STATUS_FARBE[agent.status]}`}
                  />
                  <span className="truncate font-medium">{agent.name}</span>
                </div>
                <p className="mt-1 text-xs text-[var(--color-text-leise)]">{agent.rolle}</p>
                <p className="mt-1 text-[11px] text-[var(--color-text-leise)]">
                  {STATUS_TEXT[agent.status]} · {agent.modell} · max. {agent.max_risiko}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setLoeschKandidat(agent.id)}
                aria-label={`Agent ${agent.name} loeschen`}
                title={`Agent ${agent.name} loeschen`}
                className="shrink-0 rounded px-1.5 text-[var(--color-text-leise)] hover:bg-[var(--color-flaeche-2)] hover:text-red-500"
              >
                ×
              </button>
            </div>

            {loeschKandidat === agent.id && (
              <div
                role="alertdialog"
                aria-label={`Agent ${agent.name} wirklich loeschen?`}
                className="mt-2 rounded border border-[var(--color-rand)] bg-[var(--color-flaeche-2)] p-2 text-xs"
              >
                <p>
                  Agent <strong>{agent.name}</strong> wirklich loeschen?
                </p>
                <div className="mt-2 flex gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      agentsSetzen(agents.filter((a) => a.id !== agent.id));
                      setLoeschKandidat(null);
                    }}
                    className="rounded bg-red-600 px-2 py-1 font-medium text-white"
                  >
                    Loeschen
                  </button>
                  <button
                    type="button"
                    autoFocus
                    onClick={() => setLoeschKandidat(null)}
                    className="rounded border border-[var(--color-rand)] px-2 py-1"
                  >
                    Abbrechen
                  </button>
                </div>
              </div>
            )}
          </li>
        ))}
      </ul>

      <p className="p-3 text-xs text-[var(--color-text-leise)]">
        Das sind die drei Vorlagen. Echte Agents mit eigener agent.yaml kommen in Etappe 6.
      </p>
    </Panel>
  );
}
