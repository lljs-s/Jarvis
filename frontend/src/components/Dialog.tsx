/**
 * Ein einfacher, vollstaendig tastaturbedienbarer Dialog.
 *
 * Escape schliesst, der Fokus springt beim Oeffnen hinein und beim
 * Schliessen zurueck. Bewusst selbst gebaut statt einer weiteren
 * Abhaengigkeit - es sind 40 Zeilen.
 */

import { useEffect, useRef, type ReactNode } from "react";

interface Props {
  offen: boolean;
  titel: string;
  beschreibung?: string;
  schliessen: () => void;
  children: ReactNode;
}

export function Dialog({ offen, titel, beschreibung, schliessen, children }: Props) {
  const inhalt = useRef<HTMLDivElement>(null);
  const vorherigerFokus = useRef<Element | null>(null);

  useEffect(() => {
    if (!offen) return;
    vorherigerFokus.current = document.activeElement;
    // Hat ein Feld im Dialog schon den Fokus (autoFocus), bleibt er dort.
    if (!inhalt.current?.contains(document.activeElement)) inhalt.current?.focus();
    return () => {
      (vorherigerFokus.current as HTMLElement | null)?.focus?.();
    };
  }, [offen]);

  if (!offen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 p-4 pt-[10vh]"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) schliessen();
      }}
    >
      <div
        ref={inhalt}
        role="dialog"
        aria-modal="true"
        aria-label={titel}
        tabIndex={-1}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            e.stopPropagation();
            schliessen();
          }
        }}
        className="w-full max-w-2xl overflow-hidden rounded-lg border border-[var(--color-rand)] bg-[var(--color-flaeche)] shadow-2xl"
      >
        <div className="border-b border-[var(--color-rand)] px-4 py-3">
          <h2 className="font-semibold">{titel}</h2>
          {beschreibung && (
            <p className="mt-1 text-xs text-[var(--color-text-leise)]">{beschreibung}</p>
          )}
        </div>
        {children}
      </div>
    </div>
  );
}
