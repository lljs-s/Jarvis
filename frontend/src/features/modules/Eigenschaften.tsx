/**
 * Eigenschaften des gewaehlten Eintrags - vor allem: welche Datenschutzstufe
 * gilt, WOHER sie kommt und warum sie festgeschrieben wurde.
 *
 * Senken geht nur bis zur geerbten Stufe (der Server prueft das ohnehin).
 * Wird dadurch irgendetwas lockerer, fragt der Server nach - dann zeigen wir
 * genau, was betroffen ist, und erst ein ausdrueckliches Ja fuehrt es aus.
 */

import { useState } from "react";
import { Dialog } from "../../components/Dialog";
import { api, type KnotenInfo, type Stufe } from "../../lib/api";
import { aendern, fehlertext, melde } from "./aenderung";
import { STUFEN_TEXT, waehlbareStufen } from "./baumhilfen";

interface Props {
  knoten: KnotenInfo;
}

export function Eigenschaften({ knoten }: Props) {
  const [rueckfrage, setRueckfrage] = useState<{ stufe: Stufe | null; betroffene: string[] } | null>(
    null,
  );
  const [fehler, setFehler] = useState<string | null>(null);
  const stufe = STUFEN_TEXT[knoten.datenschutz];
  const istWurzel = knoten.id === "wurzel";

  const setzen = async (neu: Stufe | null, bestaetigt: boolean) => {
    setFehler(null);
    try {
      const antwort = await aendern(() => api.datenschutzSetzen(knoten.id, neu, bestaetigt));
      if (antwort.braucht_bestaetigung) {
        setRueckfrage({ stufe: neu, betroffene: antwort.betroffene });
      } else {
        setRueckfrage(null);
      }
    } catch (f) {
      setFehler(fehlertext(f));
      melde([fehlertext(f)], "warnung");
    }
  };

  const art =
    knoten.art === "bereich" ? "Bereich" : `Modul · ${knoten.typ_name ?? knoten.typ ?? "?"}`;

  return (
    <section
      aria-label="Eigenschaften"
      className="border-t border-[var(--color-rand)] p-3 text-xs"
    >
      <h3 className="mb-1 text-sm font-semibold">{istWurzel ? "Wurzel" : knoten.name}</h3>
      <p className="text-[var(--color-text-leise)]">{istWurzel ? "Alle Bereiche" : art}</p>
      {knoten.beschreibung && <p className="mt-1">{knoten.beschreibung}</p>}

      {knoten.fehler && (
        <p role="alert" className="mt-2 rounded bg-red-100 p-2 text-red-900">
          Fehler: {knoten.fehler}
        </p>
      )}

      <div className="mt-3">
        <p>
          <span className="font-semibold">Datenschutz: </span>
          {stufe.kurz} {stufe.name}
        </p>
        <p className="text-[var(--color-text-leise)]" data-testid="herkunft">
          {knoten.datenschutz_herkunft}
        </p>
        {knoten.datenschutz_grund && (
          <p className="mt-1" data-testid="grund">
            Grund: {knoten.datenschutz_grund.text}
          </p>
        )}
        <p className="mt-1 text-[var(--color-text-leise)]">{stufe.erklaerung}</p>
      </div>

      <label className="mt-2 flex flex-col gap-1">
        Stufe ändern
        <select
          value={knoten.datenschutz_eigen ?? ""}
          disabled={Boolean(knoten.fehler)}
          onChange={(e) => void setzen((e.target.value || null) as Stufe | null, false)}
          className="rounded border border-[var(--color-rand)] bg-[var(--color-flaeche)] px-2 py-1"
        >
          <option value="">
            {istWurzel
              ? "Standard (offen)"
              : `Vom Bereich erben (${STUFEN_TEXT[knoten.datenschutz_mindest].name})`}
          </option>
          {waehlbareStufen(knoten).map((s) => (
            <option key={s} value={s}>
              {STUFEN_TEXT[s].name}
            </option>
          ))}
        </select>
      </label>
      {fehler && (
        <p role="alert" className="mt-1 text-red-600">
          {fehler}
        </p>
      )}

      {knoten.warnungen.length > 0 && (
        <ul className="mt-2 list-disc pl-4 text-yellow-700" aria-label="Warnungen">
          {knoten.warnungen.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      )}

      <Dialog
        offen={rueckfrage !== null}
        titel="Datenschutz wirklich lockern?"
        beschreibung="Danach dürfen mehr Modelle diese Daten sehen."
        schliessen={() => setRueckfrage(null)}
      >
        <div className="p-4 text-sm">
          <p className="mb-2">Diese Einträge werden lockerer:</p>
          <ul className="mb-4 list-disc pl-5" aria-label="Betroffene Einträge">
            {rueckfrage?.betroffene.map((b) => (
              <li key={b}>{b}</li>
            ))}
          </ul>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              autoFocus
              onClick={() => setRueckfrage(null)}
              className="rounded border border-[var(--color-rand)] px-3 py-1.5"
            >
              Abbrechen
            </button>
            <button
              type="button"
              onClick={() => rueckfrage && void setzen(rueckfrage.stufe, true)}
              className="rounded bg-red-600 px-3 py-1.5 text-white"
            >
              Ja, lockerer machen
            </button>
          </div>
        </div>
      </Dialog>
    </section>
  );
}
