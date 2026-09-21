/**
 * Die Befehlspalette (Strg+K).
 *
 * Ein Eingabefeld, eine gefilterte Liste, Pfeiltasten und Enter - der
 * schnellste Weg zu allem. Basiert auf cmdk, weil Fokusverwaltung und
 * Tastaturnavigation sonst erfahrungsgemaess voller Sonderfaelle sind.
 */

import { Command } from "cmdk";
import { useStore } from "../store/store";
import { AKTIONEN, alsText } from "../lib/shortcuts";
import { SLASHBEFEHLE } from "../lib/slash";

interface Props {
  aktionAusfuehren: (id: string) => void;
}

export function CommandPalette({ aktionAusfuehren }: Props) {
  const offen = useStore((s) => s.paletteOffen);
  const paletteSetzen = useStore((s) => s.paletteSetzen);
  const belegung = useStore((s) => s.belegung);
  const module = useStore((s) => s.module);
  const agents = useStore((s) => s.agents);

  if (!offen) return null;

  const ausfuehren = (id: string) => {
    paletteSetzen(false);
    aktionAusfuehren(id);
  };

  const flacheModule = (liste: typeof module, pfad = ""): { id: string; name: string }[] =>
    liste.flatMap((m) => {
      const name = pfad ? `${pfad} / ${m.name}` : m.name;
      return [{ id: m.id, name }, ...flacheModule(m.kinder, name)];
    });

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 p-4 pt-[12vh]"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) paletteSetzen(false);
      }}
    >
      <Command
        label="Befehlspalette"
        loop
        className="w-full max-w-xl overflow-hidden rounded-lg border border-[var(--color-rand)] bg-[var(--color-flaeche)] shadow-2xl"
        onKeyDown={(e) => {
          if (e.key === "Escape") paletteSetzen(false);
        }}
      >
        <Command.Input
          autoFocus
          placeholder="Befehl, Modul oder Agent suchen …"
          className="w-full border-b border-[var(--color-rand)] bg-transparent px-4 py-3 text-[15px] outline-none"
        />
        <Command.List className="max-h-80 overflow-auto p-2">
          <Command.Empty className="px-3 py-6 text-center text-sm text-[var(--color-text-leise)]">
            Nichts gefunden.
          </Command.Empty>

          <Command.Group
            heading="Aktionen"
            className="px-1 text-xs text-[var(--color-text-leise)]"
          >
            {AKTIONEN.map((aktion) => (
              <Command.Item
                key={aktion.id}
                value={`${aktion.titel} ${aktion.beschreibung}`}
                onSelect={() => ausfuehren(aktion.id)}
                className="flex cursor-pointer items-center justify-between rounded px-3 py-2 text-sm text-[var(--color-text)] data-[selected=true]:bg-[var(--color-akzent-leise)]"
              >
                <span>{aktion.titel}</span>
                <kbd className="rounded border border-[var(--color-rand)] px-1.5 py-0.5 text-[11px] text-[var(--color-text-leise)]">
                  {alsText(belegung[aktion.id] ?? aktion.standard)}
                </kbd>
              </Command.Item>
            ))}
          </Command.Group>

          {module.length > 0 && (
            <Command.Group
              heading="Module"
              className="px-1 text-xs text-[var(--color-text-leise)]"
            >
              {flacheModule(module).map((m) => (
                <Command.Item
                  key={m.id}
                  value={`modul ${m.name}`}
                  onSelect={() => ausfuehren(`modul:${m.id}`)}
                  className="cursor-pointer rounded px-3 py-2 text-sm text-[var(--color-text)] data-[selected=true]:bg-[var(--color-akzent-leise)]"
                >
                  {m.name}
                </Command.Item>
              ))}
            </Command.Group>
          )}

          {agents.length > 0 && (
            <Command.Group
              heading="Agents"
              className="px-1 text-xs text-[var(--color-text-leise)]"
            >
              {agents.map((a) => (
                <Command.Item
                  key={a.id}
                  value={`agent ${a.name} ${a.rolle}`}
                  onSelect={() => ausfuehren(`agent:${a.id}`)}
                  className="cursor-pointer rounded px-3 py-2 text-sm text-[var(--color-text)] data-[selected=true]:bg-[var(--color-akzent-leise)]"
                >
                  {a.name}
                  <span className="ml-2 text-xs text-[var(--color-text-leise)]">{a.rolle}</span>
                </Command.Item>
              ))}
            </Command.Group>
          )}

          <Command.Group
            heading="Slash-Befehle (im Chat)"
            className="px-1 text-xs text-[var(--color-text-leise)]"
          >
            {SLASHBEFEHLE.map((b) => (
              <Command.Item
                key={b.id}
                value={`slash ${b.name} ${b.kurz}`}
                onSelect={() => ausfuehren(`slash:${b.name}`)}
                className="cursor-pointer rounded px-3 py-2 text-sm text-[var(--color-text)] data-[selected=true]:bg-[var(--color-akzent-leise)]"
              >
                <span className="font-mono">{b.name}</span>
                <span className="ml-2 text-xs text-[var(--color-text-leise)]">{b.kurz}</span>
              </Command.Item>
            ))}
          </Command.Group>
        </Command.List>
      </Command>
    </div>
  );
}
