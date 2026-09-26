/**
 * Dialog "Neuer Ordner" / "Neues Modul".
 *
 * Name eintippen, beim Modul den Typ waehlen, Enter. Fehler des Servers
 * (Name belegt, ungueltige Zeichen ...) erscheinen direkt im Dialog.
 */

import { useEffect, useState, type FormEvent } from "react";
import { Dialog } from "../../components/Dialog";
import { api, type KnotenInfo } from "../../lib/api";
import { useStore } from "../../store/store";
import { aendern, fehlertext } from "./aenderung";
import { STUFEN_TEXT } from "./baumhilfen";

export type AnlegenModus = "ordner" | "modul";

interface Props {
  modus: AnlegenModus | null;
  ziel: KnotenInfo | null;
  schliessen: () => void;
  fertig: (neueId: string, zielId: string) => void;
}

export function AnlegenDialog({ modus, ziel, schliessen, fertig }: Props) {
  const typen = useStore((s) => s.typen);
  const [name, setName] = useState("");
  const [typ, setTyp] = useState("");
  const [fehler, setFehler] = useState<string | null>(null);
  const [laeuft, setLaeuft] = useState(false);

  useEffect(() => {
    if (!modus) return;
    setName("");
    setFehler(null);
    setTyp(typen[0]?.id ?? "");
  }, [modus, typen]);

  if (!modus || !ziel) return null;

  const zielName = ziel.pfad || "Wurzel";
  const absenden = async (e: FormEvent) => {
    e.preventDefault();
    setLaeuft(true);
    setFehler(null);
    try {
      const antwort = await aendern(() =>
        modus === "ordner"
          ? api.ordnerAnlegen(ziel.id, name)
          : api.modulAnlegen(ziel.id, name, typ),
      );
      if (antwort.knoten_id) fertig(antwort.knoten_id, ziel.id);
      schliessen();
    } catch (f) {
      setFehler(fehlertext(f));
    } finally {
      setLaeuft(false);
    }
  };

  return (
    <Dialog
      offen
      titel={modus === "ordner" ? "Neuer Ordner" : "Neues Modul"}
      beschreibung={`Wird angelegt in: ${zielName} (Datenschutz dort: ${STUFEN_TEXT[ziel.datenschutz].name})`}
      schliessen={schliessen}
    >
      <form onSubmit={absenden} className="flex flex-col gap-3 p-4 text-sm">
        <label className="flex flex-col gap-1">
          Name
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={80}
            className="rounded border border-[var(--color-rand)] bg-transparent px-2 py-1.5"
          />
        </label>
        {modus === "modul" && (
          <label className="flex flex-col gap-1">
            Modultyp
            <select
              value={typ}
              onChange={(e) => setTyp(e.target.value)}
              className="rounded border border-[var(--color-rand)] bg-[var(--color-flaeche)] px-2 py-1.5"
            >
              {typen.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} – {t.beschreibung}
                </option>
              ))}
            </select>
          </label>
        )}
        {fehler && (
          <p role="alert" className="text-red-600">
            {fehler}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={schliessen}
            className="rounded border border-[var(--color-rand)] px-3 py-1.5 hover:bg-[var(--color-flaeche-2)]"
          >
            Abbrechen
          </button>
          <button
            type="submit"
            disabled={laeuft || !name}
            className="rounded bg-[var(--color-akzent)] px-3 py-1.5 text-white disabled:opacity-50"
          >
            Anlegen
          </button>
        </div>
      </form>
    </Dialog>
  );
}
