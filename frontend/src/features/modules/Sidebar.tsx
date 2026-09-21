/**
 * Die Seitenleiste mit dem Modulbaum.
 *
 * Der Baum ist vollstaendig per Tastatur bedienbar (Pfeiltasten auf/ab,
 * rechts oeffnet, links schliesst, Enter waehlt) und meldet sich der
 * Bedienhilfe als echter Baum (role="tree"). Ab Etappe 2 kommen die
 * Eintraege aus den echten Ordnern unter workspace/modules/.
 */

import { useState } from "react";
import { Panel } from "../../components/Panel";
import { useStore, neueId } from "../../store/store";
import type { ModulInfo } from "../../lib/api";

export function Sidebar() {
  const module = useStore((s) => s.module);
  const gewaehlt = useStore((s) => s.gewaehltesModul);
  const waehlen = useStore((s) => s.modulWaehlen);
  const anhaengen = useStore((s) => s.nachrichtAnhaengen);
  const [offene, setOffene] = useState<Set<string>>(new Set(["privat", "privat/schule"]));

  const umschalten = (id: string) =>
    setOffene((alt) => {
      const neu = new Set(alt);
      if (neu.has(id)) neu.delete(id);
      else neu.add(id);
      return neu;
    });

  const anlegen = () => {
    anhaengen({
      id: neueId("sys"),
      absender: "system",
      text:
        "Module und Ordner anlegen kommt in Etappe 2. Ein Modul ist dann ein echter " +
        "Ordner unter workspace/modules/ mit einer module.json - die Seitenleiste " +
        "zeigt genau die Ordnerstruktur von der Festplatte.",
    });
  };

  const zeichne = (eintrag: ModulInfo, ebene: number): React.ReactNode => {
    const hatKinder = eintrag.kinder.length > 0;
    const istOffen = offene.has(eintrag.id);
    const istGewaehlt = gewaehlt === eintrag.id;

    return (
      <li key={eintrag.id} role="none">
        <div
          role="treeitem"
          aria-selected={istGewaehlt}
          aria-expanded={hatKinder ? istOffen : undefined}
          tabIndex={0}
          onClick={() => (hatKinder ? umschalten(eintrag.id) : waehlen(eintrag.id))}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              if (hatKinder) umschalten(eintrag.id);
              else waehlen(eintrag.id);
            }
            if (e.key === "ArrowRight" && hatKinder && !istOffen) umschalten(eintrag.id);
            if (e.key === "ArrowLeft" && hatKinder && istOffen) umschalten(eintrag.id);
            if (e.key === "ArrowDown" || e.key === "ArrowUp") {
              e.preventDefault();
              const alle = Array.from(
                document.querySelectorAll<HTMLElement>('[role="treeitem"]'),
              );
              const jetzt = alle.indexOf(e.currentTarget);
              const ziel = e.key === "ArrowDown" ? jetzt + 1 : jetzt - 1;
              alle[ziel]?.focus();
            }
          }}
          style={{ paddingLeft: `${ebene * 14 + 8}px` }}
          className={`flex cursor-pointer items-center gap-1.5 py-1.5 pr-2 text-sm hover:bg-[var(--color-flaeche-2)] ${
            istGewaehlt ? "bg-[var(--color-akzent-leise)] text-[var(--color-akzent)]" : ""
          }`}
        >
          <span aria-hidden className="w-3 text-[10px] text-[var(--color-text-leise)]">
            {hatKinder ? (istOffen ? "▾" : "▸") : ""}
          </span>
          <span aria-hidden>{eintrag.typ === "ordner" ? "📁" : "📄"}</span>
          <span className="truncate">{eintrag.name}</span>
        </div>
        {hatKinder && istOffen && (
          <ul role="group">{eintrag.kinder.map((kind) => zeichne(kind, ebene + 1))}</ul>
        )}
      </li>
    );
  };

  return (
    <Panel
      titel="Module"
      kuerzel="Strg+B"
      werkzeuge={
        <button
          type="button"
          onClick={anlegen}
          aria-label="Neues Modul oder neuen Ordner anlegen"
          title="Neues Modul oder neuen Ordner anlegen"
          className="rounded border border-[var(--color-rand)] px-2 py-0.5 text-sm hover:bg-[var(--color-flaeche-2)]"
        >
          +
        </button>
      }
      className="w-60 shrink-0"
    >
      {module.length === 0 ? (
        <p className="p-3 text-xs text-[var(--color-text-leise)]">Noch keine Module.</p>
      ) : (
        <ul role="tree" aria-label="Modulbaum" className="py-1">
          {module.map((eintrag) => zeichne(eintrag, 0))}
        </ul>
      )}
    </Panel>
  );
}
