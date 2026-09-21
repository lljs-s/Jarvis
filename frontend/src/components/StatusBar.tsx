/**
 * Die Statusleiste unten: was laeuft, was kostet es, wo arbeitet Jarvis.
 *
 * Kosten kommen in USD vom Server und werden hier in EUR angezeigt -
 * gerechnet wird mit dem Kurs aus den Einstellungen.
 */

import type { EinstellungenInfo, HealthInfo } from "../lib/api";

interface Props {
  health: HealthInfo | null;
  einstellungen: EinstellungenInfo | null;
}

export function StatusBar({ health, einstellungen }: Props) {
  const kosten = einstellungen?.kosten;
  return (
    <footer className="flex shrink-0 items-center justify-between gap-4 border-t border-[var(--color-rand)] bg-[var(--color-flaeche-2)] px-3 py-1.5 text-xs text-[var(--color-text-leise)]">
      <span className="truncate">
        {health ? (
          <>
            Workspace: <span title={health.workspace}>{health.workspace}</span>
            {!health.workspace_existiert && (
              <span className="ml-2 text-yellow-600">(wird beim ersten Start angelegt)</span>
            )}
          </>
        ) : (
          "Verbinde mit dem Jarvis-Server …"
        )}
      </span>
      <span className="flex shrink-0 items-center gap-4">
        {kosten && (
          <span title={`${kosten.heute_usd.toFixed(4)} USD von ${kosten.limit_tag_usd.toFixed(2)} USD`}>
            Heute: {kosten.heute_eur.toFixed(2)} EUR von {kosten.limit_tag_eur.toFixed(2)} EUR
          </span>
        )}
        <span>{health?.ki_verbunden ? health.modell : "kein Modell verbunden (Etappe 3)"}</span>
        <span>v{health?.version ?? "?"}</span>
      </span>
    </footer>
  );
}
