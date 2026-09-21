/**
 * Einstellungen: Tastenkuerzel aendern, Werte des Servers ansehen.
 *
 * Das Aendern funktioniert so: Knopf druecken, dann die gewuenschte
 * Tastenkombination druecken. Gespeichert wird im Browser.
 */

import { useEffect, useState } from "react";
import { Dialog } from "../../components/Dialog";
import { useStore } from "../../store/store";
import { AKTIONEN, alsText, ausEreignis, type AktionsId } from "../../lib/shortcuts";
import type { EinstellungenInfo } from "../../lib/api";

interface Props {
  einstellungen: EinstellungenInfo | null;
}

export function SettingsDialog({ einstellungen }: Props) {
  const offen = useStore((s) => s.einstellungenOffen);
  const schliessen = () => useStore.getState().einstellungenSetzen(false);
  const belegung = useStore((s) => s.belegung);
  const belegungSetzen = useStore((s) => s.belegungSetzen);
  const zuruecksetzen = useStore((s) => s.belegungZuruecksetzen);
  const [aufnahme, setAufnahme] = useState<AktionsId | null>(null);

  // Waehrend der Aufnahme faengt dieser Handler JEDEN Tastendruck ab -
  // sonst wuerde Strg+K die Palette oeffnen statt zugewiesen zu werden.
  useEffect(() => {
    if (!aufnahme) return;
    const beiTaste = (e: KeyboardEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (e.key === "Escape") {
        setAufnahme(null);
        return;
      }
      const kombination = ausEreignis(e);
      if (!kombination) return;
      belegungSetzen(aufnahme, kombination);
      setAufnahme(null);
    };
    window.addEventListener("keydown", beiTaste, true);
    return () => window.removeEventListener("keydown", beiTaste, true);
  }, [aufnahme, belegungSetzen]);

  return (
    <Dialog
      offen={offen}
      titel="Einstellungen"
      beschreibung="Tastenkuerzel gelten sofort und bleiben in diesem Browser gespeichert."
      schliessen={schliessen}
    >
      <div className="max-h-[60vh] overflow-auto p-4">
        <h3 className="mb-2 text-xs font-semibold uppercase text-[var(--color-text-leise)]">
          Tastenkuerzel
        </h3>
        <table className="w-full text-sm">
          <tbody>
            {AKTIONEN.map((aktion) => (
              <tr key={aktion.id} className="border-b border-[var(--color-rand)] last:border-0">
                <td className="py-2">
                  <div>{aktion.titel}</div>
                  <div className="text-xs text-[var(--color-text-leise)]">
                    {aktion.beschreibung}
                  </div>
                </td>
                <td className="w-40 py-2 text-right">
                  <button
                    type="button"
                    onClick={() => setAufnahme(aktion.id)}
                    className="rounded border border-[var(--color-rand)] px-2 py-1 font-mono text-xs hover:bg-[var(--color-flaeche-2)]"
                  >
                    {aufnahme === aktion.id
                      ? "Taste druecken …"
                      : alsText(belegung[aktion.id] ?? aktion.standard)}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <button
          type="button"
          onClick={zuruecksetzen}
          className="mt-3 rounded border border-[var(--color-rand)] px-2 py-1 text-xs hover:bg-[var(--color-flaeche-2)]"
        >
          Auf Standard zuruecksetzen
        </button>

        {einstellungen && (
          <>
            <h3 className="mt-6 mb-2 text-xs font-semibold uppercase text-[var(--color-text-leise)]">
              Vom Server
            </h3>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
              <dt className="text-[var(--color-text-leise)]">Modell</dt>
              <dd className="font-mono text-xs">{einstellungen.modell}</dd>
              <dt className="text-[var(--color-text-leise)]">Schritte je Aufgabe</dt>
              <dd>{einstellungen.max_steps}</dd>
              <dt className="text-[var(--color-text-leise)]">Kurs USD zu EUR</dt>
              <dd>{einstellungen.kosten.kurs_usd_zu_eur}</dd>
              <dt className="text-[var(--color-text-leise)]">Limit pro Tag</dt>
              <dd>
                {einstellungen.kosten.limit_tag_eur.toFixed(2)} EUR
                <span className="ml-1 text-xs text-[var(--color-text-leise)]">
                  ({einstellungen.kosten.limit_tag_usd.toFixed(2)} USD)
                </span>
              </dd>
            </dl>
            <p className="mt-2 text-xs text-[var(--color-text-leise)]">
              Diese Werte stehen in der .env-Datei. Kosten werden intern in USD gezaehlt,
              angezeigt in EUR.
            </p>
          </>
        )}
      </div>
    </Dialog>
  );
}
