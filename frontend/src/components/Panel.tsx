/**
 * Ein Panel ist ein abgegrenzter Bereich mit Titelzeile.
 *
 * Schon jetzt eine eigene Komponente, weil in Etappe 7 genau diese Bereiche
 * andockbar und verschiebbar werden (dockview). Dann aendert sich nur die
 * Huelle, nicht der Inhalt.
 */

import type { ReactNode } from "react";

interface Props {
  titel: string;
  kuerzel?: string;
  werkzeuge?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Panel({ titel, kuerzel, werkzeuge, children, className = "" }: Props) {
  return (
    <section
      aria-label={titel}
      className={`flex min-h-0 flex-col border-[var(--color-rand)] bg-[var(--color-flaeche)] ${className}`}
    >
      <header className="flex shrink-0 items-center justify-between gap-2 border-b border-[var(--color-rand)] px-3 py-2">
        <h2 className="text-xs font-semibold tracking-wide text-[var(--color-text-leise)] uppercase">
          {titel}
          {kuerzel && (
            <span className="ml-2 font-normal normal-case opacity-70">{kuerzel}</span>
          )}
        </h2>
        {werkzeuge}
      </header>
      <div className="min-h-0 flex-1 overflow-auto">{children}</div>
    </section>
  );
}
