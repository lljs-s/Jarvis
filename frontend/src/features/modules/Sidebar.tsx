/**
 * Die Seitenleiste mit dem Modulbaum - die echten Ordner aus <Workspace>/bereiche.
 *
 * Alles geht per Maus UND per Tastatur:
 *
 *   Pfeil auf/ab        naechster/voriger Eintrag
 *   Pfeil rechts/links  Bereich auf-/zuklappen
 *   Enter / Leertaste   auswaehlen (Eigenschaften unten)
 *   F2                  umbenennen (Enter speichert, Escape bricht ab)
 *   Strg+X, Strg+V      verschieben: ausschneiden, dann auf einem Bereich einfuegen
 *   Escape              Ausschneiden abbrechen
 *   Ziehen & Ablegen    verschieben mit der Maus (auf leere Flaeche = in die Wurzel)
 *
 * Der Baum meldet sich der Bedienhilfe als echter Baum (role="tree").
 */

import { useEffect, useRef, useState, type DragEvent, type KeyboardEvent } from "react";
import { Panel } from "../../components/Panel";
import { api, type KnotenInfo } from "../../lib/api";
import { useStore } from "../../store/store";
import { aendern, fehlertext, melde } from "./aenderung";
import { AnlegenDialog, type AnlegenModus } from "./AnlegenDialog";
import { Eigenschaften } from "./Eigenschaften";
import {
  bereicheBisTiefe,
  farbWert,
  finde,
  STUFEN_TEXT,
  symbolZeichen,
  zielBereich,
} from "./baumhilfen";

export function Sidebar() {
  const wurzel = useStore((s) => s.wurzel);
  const module = useStore((s) => s.module);
  const gewaehlt = useStore((s) => s.gewaehltesModul);
  const waehlen = useStore((s) => s.modulWaehlen);

  const [offene, setOffene] = useState<Set<string>>(new Set());
  const aufgeklappt = useRef(false);
  const [menueOffen, setMenueOffen] = useState(false);
  const [anlegen, setAnlegen] = useState<AnlegenModus | null>(null);
  const [umbenennen, setUmbenennen] = useState<{ id: string; name: string } | null>(null);
  const [ausgeschnitten, setAusgeschnitten] = useState<string | null>(null);
  const [ablageZiel, setAblageZiel] = useState<string | null>(null);
  const [meldung, setMeldung] = useState("");
  const baumRef = useRef<HTMLUListElement>(null);
  const menueRef = useRef<HTMLDivElement>(null);

  // Beim ersten Laden die oberste Ebene aufklappen.
  useEffect(() => {
    if (aufgeklappt.current || module.length === 0) return;
    aufgeklappt.current = true;
    setOffene(new Set(bereicheBisTiefe(module, 1)));
  }, [module]);

  // Menue: Fokus auf den ersten Eintrag.
  useEffect(() => {
    if (menueOffen) menueRef.current?.querySelector<HTMLElement>('[role="menuitem"]')?.focus();
  }, [menueOffen]);

  const oeffne = (id: string) => setOffene((alt) => new Set(alt).add(id));
  const umschalten = (id: string) =>
    setOffene((alt) => {
      const neu = new Set(alt);
      if (neu.has(id)) neu.delete(id);
      else neu.add(id);
      return neu;
    });

  // Nach einer Aenderung zeichnet React neu - danach den Fokus zurueckholen.
  const fokussiere = (id: string) =>
    setTimeout(
      () => baumRef.current?.querySelector<HTMLElement>(`[data-id="${CSS.escape(id)}"]`)?.focus(),
      0,
    );

  const verschiebe = async (id: string, zielId: string) => {
    setAusgeschnitten(null);
    setAblageZiel(null);
    const knoten = finde(wurzel, id);
    const ziel = finde(wurzel, zielId);
    if (!knoten || !ziel) return;
    try {
      await aendern(() => api.verschieben(id, zielId));
      oeffne(zielId);
      setMeldung(`„${knoten.name}“ liegt jetzt in „${ziel.pfad || "Wurzel"}“.`);
      fokussiere(id);
    } catch (f) {
      setMeldung(fehlertext(f));
      melde([fehlertext(f)], "warnung");
    }
  };

  const umbenennenSpeichern = async () => {
    if (!umbenennen) return;
    const { id, name } = umbenennen;
    const alt = finde(wurzel, id);
    if (!alt || name === alt.name) {
      setUmbenennen(null);
      fokussiere(id);
      return;
    }
    try {
      await aendern(() => api.umbenennen(id, name));
      setUmbenennen(null);
      setMeldung(`Umbenannt in „${name}“.`);
      fokussiere(id);
    } catch (f) {
      setMeldung(fehlertext(f));
    }
  };

  const beiTaste = (e: KeyboardEvent<HTMLDivElement>, eintrag: KnotenInfo) => {
    const istBereich = eintrag.art === "bereich";
    const strg = e.ctrlKey || e.metaKey;
    let behandelt = true;

    if (e.key === "Enter" || e.key === " ") {
      waehlen(eintrag.id);
      if (istBereich) umschalten(eintrag.id);
    } else if (e.key === "ArrowRight" && istBereich) {
      oeffne(eintrag.id);
    } else if (e.key === "ArrowLeft" && istBereich) {
      setOffene((alt) => {
        const neu = new Set(alt);
        neu.delete(eintrag.id);
        return neu;
      });
    } else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      const alle = Array.from(
        baumRef.current?.querySelectorAll<HTMLElement>('[role="treeitem"]') ?? [],
      );
      const jetzt = alle.indexOf(e.currentTarget);
      alle[e.key === "ArrowDown" ? jetzt + 1 : jetzt - 1]?.focus();
    } else if (e.key === "F2" && !eintrag.fehler) {
      setUmbenennen({ id: eintrag.id, name: eintrag.name });
    } else if (strg && e.key.toLowerCase() === "x" && !eintrag.fehler) {
      setAusgeschnitten(eintrag.id);
      setMeldung(
        `„${eintrag.name}“ zum Verschieben markiert. Wähle einen Bereich und drücke Strg+V. Escape bricht ab.`,
      );
    } else if (strg && e.key.toLowerCase() === "v" && ausgeschnitten) {
      const ziel = zielBereich(wurzel, eintrag.id);
      if (ziel) void verschiebe(ausgeschnitten, ziel.id);
    } else if (e.key === "Escape" && ausgeschnitten) {
      setAusgeschnitten(null);
      setMeldung("Verschieben abgebrochen.");
    } else {
      behandelt = false;
    }

    if (behandelt) {
      e.preventDefault();
      e.stopPropagation(); // sonst reagieren die globalen Tastenkuerzel mit
    }
  };

  // -- Ziehen & Ablegen ------------------------------------------------------

  const ziehenStart = (e: DragEvent<HTMLDivElement>, eintrag: KnotenInfo) => {
    e.dataTransfer.setData("text/plain", eintrag.id);
    e.dataTransfer.effectAllowed = "move";
  };

  const ueberZiel = (e: DragEvent<HTMLElement>, zielId: string) => {
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = "move";
    setAblageZiel(zielId);
  };

  const ablegen = (e: DragEvent<HTMLElement>, zielId: string) => {
    e.preventDefault();
    e.stopPropagation();
    const id = e.dataTransfer.getData("text/plain");
    if (id && id !== zielId) void verschiebe(id, zielId);
    setAblageZiel(null);
  };

  // -- Zeichnen --------------------------------------------------------------

  const zeichne = (eintrag: KnotenInfo, ebene: number): React.ReactNode => {
    const istBereich = eintrag.art === "bereich";
    const hatKinder = eintrag.kinder.length > 0;
    const istOffen = offene.has(eintrag.id);
    const istGewaehlt = gewaehlt === eintrag.id;
    const stufe = STUFEN_TEXT[eintrag.datenschutz];
    const kannZiel = istBereich && !eintrag.fehler;

    return (
      <li key={eintrag.id} role="none">
        <div
          role="treeitem"
          data-id={eintrag.id}
          aria-label={`${eintrag.name}, ${stufe.name}${eintrag.fehler ? ", fehlerhaft" : ""}`}
          aria-selected={istGewaehlt}
          aria-expanded={istBereich && hatKinder ? istOffen : undefined}
          aria-level={ebene + 1}
          tabIndex={0}
          draggable={!eintrag.fehler && !umbenennen}
          onDragStart={(e) => ziehenStart(e, eintrag)}
          onDragOver={kannZiel ? (e) => ueberZiel(e, eintrag.id) : undefined}
          onDragLeave={() => setAblageZiel(null)}
          onDrop={kannZiel ? (e) => ablegen(e, eintrag.id) : undefined}
          onClick={() => {
            waehlen(eintrag.id);
            if (istBereich && hatKinder) umschalten(eintrag.id);
          }}
          onKeyDown={(e) => beiTaste(e, eintrag)}
          style={{ paddingLeft: `${ebene * 14 + 8}px` }}
          className={`flex cursor-pointer items-center gap-1.5 py-1.5 pr-2 text-sm hover:bg-[var(--color-flaeche-2)] ${
            istGewaehlt ? "bg-[var(--color-akzent-leise)] text-[var(--color-akzent)]" : ""
          } ${ausgeschnitten === eintrag.id ? "opacity-50" : ""} ${
            ablageZiel === eintrag.id ? "outline-2 outline-dashed outline-[var(--color-akzent)]" : ""
          }`}
        >
          <span aria-hidden className="w-3 text-[10px] text-[var(--color-text-leise)]">
            {istBereich && hatKinder ? (istOffen ? "▾" : "▸") : ""}
          </span>
          <span
            aria-hidden
            className="inline-block h-2 w-2 shrink-0 rounded-full"
            style={{ background: farbWert(eintrag.farbe) }}
          />
          <span aria-hidden>{symbolZeichen(eintrag.symbol)}</span>
          {umbenennen?.id === eintrag.id ? (
            <input
              autoFocus
              aria-label="Neuer Name"
              value={umbenennen.name}
              maxLength={80}
              onChange={(e) => setUmbenennen({ id: eintrag.id, name: e.target.value })}
              onClick={(e) => e.stopPropagation()}
              onKeyDown={(e) => {
                e.stopPropagation();
                if (e.key === "Enter") void umbenennenSpeichern();
                if (e.key === "Escape") {
                  setUmbenennen(null);
                  fokussiere(eintrag.id);
                }
              }}
              className="min-w-0 flex-1 rounded border border-[var(--color-akzent)] bg-[var(--color-flaeche)] px-1 text-[var(--color-text)]"
            />
          ) : (
            <span className="truncate">{eintrag.name}</span>
          )}
          <span className="ml-auto flex shrink-0 gap-1 text-xs">
            {eintrag.fehler && (
              <span title={eintrag.fehler} aria-hidden>
                ⚠️
              </span>
            )}
            {!eintrag.fehler && eintrag.warnungen.length > 0 && (
              <span title={eintrag.warnungen.join("\n")} aria-hidden className="text-yellow-600">
                !
              </span>
            )}
            {stufe.kurz && (
              <span title={`${stufe.name} – ${eintrag.datenschutz_herkunft}`} aria-hidden>
                {stufe.kurz}
              </span>
            )}
          </span>
        </div>
        {istBereich && hatKinder && istOffen && (
          <ul role="group">{eintrag.kinder.map((kind) => zeichne(kind, ebene + 1))}</ul>
        )}
      </li>
    );
  };

  const gewaehlterKnoten = finde(wurzel, gewaehlt);
  const ziel = zielBereich(wurzel, gewaehlt);

  const menueTaste = (e: KeyboardEvent<HTMLDivElement>) => {
    const eintraege = Array.from(
      menueRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? [],
    );
    const jetzt = eintraege.indexOf(document.activeElement as HTMLElement);
    if (e.key === "ArrowDown") eintraege[(jetzt + 1) % eintraege.length]?.focus();
    else if (e.key === "ArrowUp")
      eintraege[(jetzt - 1 + eintraege.length) % eintraege.length]?.focus();
    else if (e.key === "Escape") setMenueOffen(false);
    else return;
    e.preventDefault();
    e.stopPropagation();
  };

  const waehleAnlegen = (modus: AnlegenModus) => {
    setMenueOffen(false);
    setAnlegen(modus);
  };

  return (
    <Panel
      titel="Module"
      kuerzel="Strg+B"
      werkzeuge={
        <div className="relative">
          <button
            type="button"
            onClick={() => setMenueOffen((o) => !o)}
            aria-label="Neuen Ordner oder neues Modul anlegen"
            aria-haspopup="menu"
            aria-expanded={menueOffen}
            title="Neuen Ordner oder neues Modul anlegen"
            className="rounded border border-[var(--color-rand)] px-2 py-0.5 text-sm hover:bg-[var(--color-flaeche-2)]"
          >
            +
          </button>
          {menueOffen && (
            <div
              ref={menueRef}
              role="menu"
              aria-label="Anlegen"
              onKeyDown={menueTaste}
              className="absolute right-0 z-40 mt-1 w-44 overflow-hidden rounded border border-[var(--color-rand)] bg-[var(--color-flaeche)] py-1 text-sm shadow-lg"
            >
              <button
                type="button"
                role="menuitem"
                onClick={() => waehleAnlegen("ordner")}
                className="block w-full px-3 py-1.5 text-left hover:bg-[var(--color-flaeche-2)] focus:bg-[var(--color-akzent-leise)]"
              >
                📁 Neuer Ordner
              </button>
              <button
                type="button"
                role="menuitem"
                onClick={() => waehleAnlegen("modul")}
                className="block w-full px-3 py-1.5 text-left hover:bg-[var(--color-flaeche-2)] focus:bg-[var(--color-akzent-leise)]"
              >
                📄 Neues Modul
              </button>
            </div>
          )}
        </div>
      }
      className="w-64 shrink-0"
    >
      <div className="flex h-full flex-col">
        <div
          data-testid="baumflaeche"
          className="min-h-0 flex-1 overflow-auto"
          onDragOver={wurzel ? (e) => ueberZiel(e, wurzel.id) : undefined}
          onDrop={wurzel ? (e) => ablegen(e, wurzel.id) : undefined}
        >
          {module.length === 0 ? (
            <p className="p-3 text-xs text-[var(--color-text-leise)]">
              Noch keine Bereiche. Mit „+“ legst du den ersten an.
            </p>
          ) : (
            <ul ref={baumRef} role="tree" aria-label="Modulbaum" className="py-1">
              {module.map((eintrag) => zeichne(eintrag, 0))}
            </ul>
          )}
        </div>
        <p
          role="status"
          aria-live="polite"
          className="px-3 py-1 text-xs text-[var(--color-text-leise)]"
        >
          {meldung}
        </p>
        {gewaehlterKnoten && <Eigenschaften knoten={gewaehlterKnoten} />}
      </div>

      <AnlegenDialog
        modus={anlegen}
        ziel={ziel}
        schliessen={() => setAnlegen(null)}
        fertig={(neueId, zielId) => {
          oeffne(zielId);
          waehlen(neueId);
          setMeldung("Angelegt.");
          fokussiere(neueId);
        }}
      />
    </Panel>
  );
}
