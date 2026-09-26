/**
 * Der Modulbaum in der Oberflaeche - jede Bedienung per Maus UND Tastatur.
 *
 * Der Server ist eine Attrappe, die jede Anfrage mitschreibt. So pruefen
 * die Tests, WAS die Oberflaeche an den Server schickt.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Sidebar } from "./Sidebar";
import { useStore } from "../../store/store";
import type { AenderungsAntwort, KnotenInfo } from "../../lib/api";
import { knoten, TYPEN, wurzel } from "../../test-daten";

const KUNDEN = knoten({
  id: "mod_kunden01",
  name: "Kunden",
  pfad: "Unternehmen/Kunden",
  art: "modul",
  typ: "notizen",
  typ_name: "Notizen",
  datenschutz: "vertraulich",
  datenschutz_mindest: "vertraulich",
  datenschutz_herkunft: "geerbt von Unternehmen",
});
const UNTERNEHMEN = knoten({
  id: "ord_untern01",
  name: "Unternehmen",
  datenschutz: "vertraulich",
  datenschutz_eigen: "vertraulich",
  datenschutz_herkunft: "eigene Einstellung",
  datenschutz_grund: {
    art: "gesetzt",
    text: "bei der Einrichtung festgelegt am 26.09.2026",
    datum: "2026-09-26",
  },
  kinder: [KUNDEN],
});
const PRIVAT = knoten({ id: "ord_privat01", name: "Privat" });
const KAPUTT = knoten({
  id: "ord_kaputt01",
  name: "Kaputt",
  fehler: "folder.json ist kein gueltiges JSON",
  datenschutz: "lokal",
  datenschutz_mindest: "lokal",
});
const BAUM = wurzel([PRIVAT, UNTERNEHMEN, KAPUTT]);

interface Aufruf {
  url: string;
  daten: Record<string, unknown> | undefined;
}

let aufrufe: Aufruf[] = [];
let antwort: (url: string, daten: Record<string, unknown> | undefined) => {
  status: number;
  body: unknown;
};

function ok(baum: KnotenInfo = BAUM, extra: Partial<AenderungsAntwort> = {}) {
  const body: AenderungsAntwort = {
    baum,
    knoten_id: null,
    warnungen: [],
    hinweise: [],
    braucht_bestaetigung: false,
    betroffene: [],
    ...extra,
  };
  return { status: 200, body };
}

beforeEach(() => {
  aufrufe = [];
  antwort = () => ok();
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string, init?: RequestInit) => {
      const daten = init?.body
        ? (JSON.parse(init.body as string) as Record<string, unknown>)
        : undefined;
      aufrufe.push({ url, daten });
      const { status, body } = antwort(url, daten);
      return Promise.resolve({
        ok: status < 400,
        status,
        json: () => Promise.resolve(body),
      } as Response);
    }),
  );
  useStore.setState({ nachrichten: [], gewaehltesModul: null });
  useStore.getState().baumSetzen(BAUM);
  useStore.getState().typenSetzen(TYPEN);
});

const eintrag = (name: RegExp) => screen.getByRole("treeitem", { name });

describe("Anzeige", () => {
  it("zeigt die echten Bereiche mit ihrer Stufe", () => {
    render(<Sidebar />);
    expect(eintrag(/^Unternehmen, Vertraulich/)).toBeInTheDocument();
    expect(eintrag(/^Kunden, Vertraulich/)).toBeInTheDocument();
    expect(eintrag(/^Kaputt, Lokal, fehlerhaft/)).toBeInTheDocument();
  });

  it("zeigt Herkunft und Grund der Datenschutzstufe", async () => {
    const nutzer = userEvent.setup();
    render(<Sidebar />);
    await nutzer.click(eintrag(/^Unternehmen/));
    const eigenschaften = screen.getByRole("region", { name: "Eigenschaften" });
    expect(within(eigenschaften).getByTestId("herkunft")).toHaveTextContent("eigene Einstellung");
    expect(within(eigenschaften).getByTestId("grund")).toHaveTextContent(
      "bei der Einrichtung festgelegt am 26.09.2026",
    );
  });
});

describe("Datenschutz aendern", () => {
  it("bietet keine Stufe unter der geerbten an", async () => {
    const nutzer = userEvent.setup();
    render(<Sidebar />);
    await nutzer.click(eintrag(/^Kunden/));
    const auswahl = screen.getByRole("combobox", { name: "Stufe ändern" });
    const optionen = within(auswahl)
      .getAllByRole("option")
      .map((o) => o.textContent);
    expect(optionen).toEqual(["Vom Bereich erben (Vertraulich)", "Vertraulich", "Lokal"]);
  });

  it("senken nur nach ausdruecklichem Ja - mit Liste der Betroffenen", async () => {
    const nutzer = userEvent.setup();
    antwort = (_url, daten) =>
      daten?.bestaetigt
        ? ok()
        : ok(BAUM, {
            braucht_bestaetigung: true,
            betroffene: ["Unternehmen: vertraulich -> offen", "Unternehmen/Kunden: vertraulich -> offen"],
          });
    render(<Sidebar />);
    await nutzer.click(eintrag(/^Unternehmen/));
    await nutzer.selectOptions(screen.getByRole("combobox", { name: "Stufe ändern" }), "");

    const dialog = await screen.findByRole("dialog", { name: "Datenschutz wirklich lockern?" });
    expect(within(dialog).getByText("Unternehmen/Kunden: vertraulich -> offen")).toBeInTheDocument();
    expect(aufrufe).toHaveLength(1);
    expect(aufrufe[0]?.daten).toEqual({ id: "ord_untern01", stufe: null, bestaetigt: false });

    await nutzer.click(within(dialog).getByRole("button", { name: "Ja, lockerer machen" }));
    await waitFor(() => expect(aufrufe).toHaveLength(2));
    expect(aufrufe[1]?.daten).toEqual({ id: "ord_untern01", stufe: null, bestaetigt: true });
  });

  it("Abbrechen schickt nichts weiter", async () => {
    const nutzer = userEvent.setup();
    antwort = () => ok(BAUM, { braucht_bestaetigung: true, betroffene: ["x"] });
    render(<Sidebar />);
    await nutzer.click(eintrag(/^Unternehmen/));
    await nutzer.selectOptions(screen.getByRole("combobox", { name: "Stufe ändern" }), "");
    const dialog = await screen.findByRole("dialog");
    await nutzer.click(within(dialog).getByRole("button", { name: "Abbrechen" }));
    expect(aufrufe).toHaveLength(1);
  });
});

describe("Anlegen ueber +", () => {
  it("Neuer Ordner im gewaehlten Bereich - nur per Tastatur", async () => {
    const nutzer = userEvent.setup();
    const neu = knoten({ id: "ord_neu00001", name: "Firma A", pfad: "Unternehmen/Firma A" });
    antwort = () =>
      ok(wurzel([PRIVAT, { ...UNTERNEHMEN, kinder: [neu, KUNDEN] }, KAPUTT]), {
        knoten_id: "ord_neu00001",
      });
    render(<Sidebar />);
    eintrag(/^Unternehmen/).focus();
    await nutzer.keyboard("{Enter}"); // auswaehlen

    screen.getByRole("button", { name: /anlegen/ }).focus();
    await nutzer.keyboard("{Enter}");
    const menue = screen.getByRole("menu", { name: "Anlegen" });
    expect(within(menue).getByRole("menuitem", { name: /Neuer Ordner/ })).toHaveFocus();
    await nutzer.keyboard("{Enter}");

    const dialog = await screen.findByRole("dialog", { name: "Neuer Ordner" });
    expect(dialog).toHaveTextContent("Wird angelegt in: Unternehmen");
    await nutzer.keyboard("Firma A{Enter}");

    await waitFor(() => expect(aufrufe).toHaveLength(1));
    expect(aufrufe[0]?.url).toBe("/api/modules/ordner");
    expect(aufrufe[0]?.daten).toEqual({ eltern_id: "ord_untern01", name: "Firma A" });
    expect(await screen.findByRole("treeitem", { name: /^Firma A/ })).toBeInTheDocument();
  });

  it("Neues Modul mit Typauswahl", async () => {
    const nutzer = userEvent.setup();
    render(<Sidebar />);
    await nutzer.click(screen.getByRole("button", { name: /anlegen/ }));
    await nutzer.click(screen.getByRole("menuitem", { name: /Neues Modul/ }));
    const dialog = await screen.findByRole("dialog", { name: "Neues Modul" });
    await nutzer.type(within(dialog).getByRole("textbox", { name: "Name" }), "Hausaufgaben");
    await nutzer.selectOptions(within(dialog).getByRole("combobox", { name: "Modultyp" }), "aufgaben");
    await nutzer.click(within(dialog).getByRole("button", { name: "Anlegen" }));

    await waitFor(() => expect(aufrufe).toHaveLength(1));
    expect(aufrufe[0]?.url).toBe("/api/modules/modul");
    expect(aufrufe[0]?.daten).toEqual({ eltern_id: "wurzel", name: "Hausaufgaben", typ: "aufgaben" });
  });

  it("zeigt die Ablehnung des Servers im Dialog", async () => {
    const nutzer = userEvent.setup();
    antwort = () => ({ status: 400, body: { fehler: "In 'Wurzel' gibt es schon 'Privat'." } });
    render(<Sidebar />);
    await nutzer.click(screen.getByRole("button", { name: /anlegen/ }));
    await nutzer.click(screen.getByRole("menuitem", { name: /Neuer Ordner/ }));
    await nutzer.keyboard("Privat{Enter}");
    const dialog = await screen.findByRole("dialog", { name: "Neuer Ordner" });
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("gibt es schon 'Privat'");
  });

  it("Escape schliesst das Menue", async () => {
    const nutzer = userEvent.setup();
    render(<Sidebar />);
    await nutzer.click(screen.getByRole("button", { name: /anlegen/ }));
    await nutzer.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });
});

describe("Umbenennen mit F2", () => {
  it("Enter speichert", async () => {
    const nutzer = userEvent.setup();
    render(<Sidebar />);
    eintrag(/^Privat/).focus();
    await nutzer.keyboard("{F2}");
    const feld = screen.getByRole("textbox", { name: "Neuer Name" });
    expect(feld).toHaveFocus();
    await nutzer.clear(feld);
    await nutzer.keyboard("Familie{Enter}");
    await waitFor(() => expect(aufrufe).toHaveLength(1));
    expect(aufrufe[0]).toEqual({
      url: "/api/modules/umbenennen",
      daten: { id: "ord_privat01", name: "Familie" },
    });
  });

  it("Escape bricht ab, ohne etwas zu schicken", async () => {
    const nutzer = userEvent.setup();
    render(<Sidebar />);
    eintrag(/^Privat/).focus();
    await nutzer.keyboard("{F2}x{Escape}");
    expect(screen.queryByRole("textbox", { name: "Neuer Name" })).not.toBeInTheDocument();
    expect(aufrufe).toHaveLength(0);
  });

  it("fehlerhafte Eintraege lassen sich nicht umbenennen", async () => {
    const nutzer = userEvent.setup();
    render(<Sidebar />);
    eintrag(/^Kaputt/).focus();
    await nutzer.keyboard("{F2}");
    expect(screen.queryByRole("textbox", { name: "Neuer Name" })).not.toBeInTheDocument();
  });
});

describe("Verschieben", () => {
  it("per Tastatur: Strg+X, dann Strg+V auf einem Bereich", async () => {
    const nutzer = userEvent.setup();
    antwort = () =>
      ok(BAUM, { warnungen: ["'Kunden' behaelt die Stufe 'vertraulich'"] });
    render(<Sidebar />);
    eintrag(/^Kunden/).focus();
    await nutzer.keyboard("{Control>}x{/Control}");
    expect(screen.getByRole("status")).toHaveTextContent("zum Verschieben markiert");

    eintrag(/^Privat/).focus();
    await nutzer.keyboard("{Control>}v{/Control}");
    await waitFor(() => expect(aufrufe).toHaveLength(1));
    expect(aufrufe[0]).toEqual({
      url: "/api/modules/verschieben",
      daten: { id: "mod_kunden01", ziel_id: "ord_privat01" },
    });
    // Die Warnung des Servers geht nicht verloren:
    await waitFor(() =>
      expect(useStore.getState().nachrichten.map((n) => n.text).join()).toContain(
        "behaelt die Stufe",
      ),
    );
  });

  it("Escape hebt das Ausschneiden auf", async () => {
    const nutzer = userEvent.setup();
    render(<Sidebar />);
    eintrag(/^Kunden/).focus();
    await nutzer.keyboard("{Control>}x{/Control}{Escape}");
    eintrag(/^Privat/).focus();
    await nutzer.keyboard("{Control>}v{/Control}");
    expect(aufrufe).toHaveLength(0);
  });

  it("per Ziehen und Ablegen", async () => {
    render(<Sidebar />);
    const speicher: Record<string, string> = {};
    const dataTransfer = {
      setData: (art: string, wert: string) => (speicher[art] = wert),
      getData: (art: string) => speicher[art] ?? "",
      dropEffect: "",
      effectAllowed: "",
    };
    fireEvent.dragStart(eintrag(/^Kunden/), { dataTransfer });
    fireEvent.dragOver(eintrag(/^Privat/), { dataTransfer });
    fireEvent.drop(eintrag(/^Privat/), { dataTransfer });
    await waitFor(() => expect(aufrufe).toHaveLength(1));
    expect(aufrufe[0]?.daten).toEqual({ id: "mod_kunden01", ziel_id: "ord_privat01" });
  });

  it("fehlerhafte Eintraege sind weder Quelle noch Ziel", () => {
    render(<Sidebar />);
    expect(eintrag(/^Kaputt/)).toHaveAttribute("draggable", "false");
    const dataTransfer = { getData: () => "mod_kunden01", setData: () => undefined };
    fireEvent.drop(eintrag(/^Kaputt/), { dataTransfer });
    // Der Drop faellt durch bis zur Baumflaeche = Wurzel, nie in "Kaputt".
    expect(aufrufe.every((a) => a.daten?.ziel_id !== "ord_kaputt01")).toBe(true);
  });
});
