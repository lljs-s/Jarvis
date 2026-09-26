/**
 * Tests der Oberflaeche: erreicht man wirklich alles per Tastatur?
 *
 * Server und WebSocket sind hier nachgebaut (Attrappen) - die Tests laufen
 * ohne Netz, ohne Python und ohne Kosten.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "./App";
import { useStore } from "../store/store";
import { standardBelegung } from "../lib/shortcuts";
import { knoten, TYPEN, wurzel } from "../test-daten";

const HEALTH = {
  status: "ok",
  version: "0.1.0",
  etappe: "1 - Grundgeruest",
  workspace: "C:\\Users\\Test\\Documents\\Jarvis-Workspace",
  workspace_existiert: true,
  modell: "claude-opus-5",
  hat_anthropic_key: true,
  hat_gemini_key: false,
  ki_verbunden: false,
};

const EINSTELLUNGEN = {
  modell: "claude-opus-5",
  max_steps: 12,
  max_read_bytes: 200000,
  kosten: {
    heute_usd: 0,
    heute_eur: 0,
    limit_tag_usd: 2,
    limit_tag_eur: 1.84,
    limit_aufgabe_usd: 0.5,
    kurs_usd_zu_eur: 0.92,
  },
};

const AGENTS = [
  {
    id: "recherche",
    name: "Recherche",
    rolle: "Sucht Informationen",
    modell: "gemini",
    status: "idle",
    max_risiko: "LOW",
    notiz: "",
  },
];

const MODULE = wurzel([
  knoten({
    id: "ord_privat01",
    name: "Privat",
    kinder: [
      knoten({ id: "mod_mathe001", name: "Mathe", pfad: "Privat/Mathe", art: "modul" }),
    ],
  }),
  knoten({ id: "ord_schule01", name: "Schule" }),
]);

/** Eine WebSocket-Attrappe, die sich wie der echte Server verhaelt. */
class FakeWebSocket {
  static letzte: FakeWebSocket | null = null;
  static OPEN = 1;
  readyState = 1;
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: ((e: { code: number }) => void) | null = null;
  onerror: (() => void) | null = null;
  gesendet: string[] = [];

  constructor(readonly url: string) {
    FakeWebSocket.letzte = this;
    setTimeout(() => this.onopen?.(), 0);
  }

  send(daten: string) {
    this.gesendet.push(daten);
    // Antwort wie der Platzhalter des Servers: start -> stueck -> ende
    setTimeout(() => {
      this.onmessage?.({ data: JSON.stringify({ typ: "start", text: "", absender: "jarvis" }) });
      this.onmessage?.({
        data: JSON.stringify({ typ: "stueck", text: "Antwort vom Server.", absender: "jarvis" }),
      });
      this.onmessage?.({ data: JSON.stringify({ typ: "ende", text: "", absender: "jarvis" }) });
    }, 0);
  }

  close() {
    this.readyState = 3;
  }
}

function serverAttrappe(url: string) {
  const daten: Record<string, unknown> = {
    "/api/health": HEALTH,
    "/api/settings": EINSTELLUNGEN,
    "/api/agents": AGENTS,
    "/api/modules": MODULE,
    "/api/modules/typen": TYPEN,
  };
  return Promise.resolve({
    ok: url in daten,
    status: url in daten ? 200 : 404,
    json: () => Promise.resolve(daten[url]),
  } as Response);
}

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  vi.stubGlobal("fetch", vi.fn((url: string) => serverAttrappe(url)));
  vi.stubGlobal("WebSocket", FakeWebSocket);
  useStore.setState({
    nachrichten: [],
    agents: [],
    wurzel: null,
    module: [],
    paletteOffen: false,
    einstellungenOffen: false,
    seitenleisteSichtbar: true,
    agentsSichtbar: true,
    thema: "hell",
    belegung: standardBelegung(),
  });
});

describe("Grundgeruest", () => {
  it("zeigt die drei Bereiche: Module, Jarvis, Agents", async () => {
    render(<App />);
    expect(await screen.findByRole("region", { name: "Module" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Jarvis" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Agents" })).toBeInTheDocument();
  });

  it("laedt Module und Agents vom Server", async () => {
    render(<App />);
    expect(await screen.findByText("Privat")).toBeInTheDocument();
    expect(await screen.findByText("Recherche")).toBeInTheDocument();
  });

  it("zeigt den Workspace-Pfad in der Statusleiste", async () => {
    render(<App />);
    expect(await screen.findByText(/Jarvis-Workspace/)).toBeInTheDocument();
  });

  it("zeigt Kosten in EUR mit dem USD-Wert als Hinweis", async () => {
    render(<App />);
    const anzeige = await screen.findByText(/Heute: 0\.00 EUR von 1\.84 EUR/);
    expect(anzeige).toHaveAttribute("title", expect.stringContaining("USD"));
  });
});

describe("Tastensteuerung", () => {
  it("Strg+K oeffnet die Befehlspalette", async () => {
    const nutzer = userEvent.setup();
    render(<App />);
    await screen.findByRole("region", { name: "Module" });

    expect(screen.queryByPlaceholderText(/Befehl, Modul oder Agent/)).not.toBeInTheDocument();
    await nutzer.keyboard("{Control>}k{/Control}");
    expect(await screen.findByPlaceholderText(/Befehl, Modul oder Agent/)).toBeInTheDocument();
  });

  it("Escape schliesst die Befehlspalette wieder", async () => {
    const nutzer = userEvent.setup();
    render(<App />);
    await nutzer.keyboard("{Control>}k{/Control}");
    await screen.findByPlaceholderText(/Befehl, Modul oder Agent/);
    await nutzer.keyboard("{Escape}");
    await waitFor(() =>
      expect(screen.queryByPlaceholderText(/Befehl, Modul oder Agent/)).not.toBeInTheDocument(),
    );
  });

  it("Strg+J springt ins Chatfeld", async () => {
    const nutzer = userEvent.setup();
    render(<App />);
    await screen.findByRole("region", { name: "Jarvis" });

    await nutzer.keyboard("{Control>}j{/Control}");
    expect(screen.getByLabelText("Nachricht an Jarvis")).toHaveFocus();
  });

  it("Strg+B blendet die Seitenleiste aus und wieder ein", async () => {
    const nutzer = userEvent.setup();
    render(<App />);
    await screen.findByRole("region", { name: "Module" });

    await nutzer.keyboard("{Control>}b{/Control}");
    await waitFor(() =>
      expect(screen.queryByRole("region", { name: "Module" })).not.toBeInTheDocument(),
    );
    await nutzer.keyboard("{Control>}b{/Control}");
    expect(await screen.findByRole("region", { name: "Module" })).toBeInTheDocument();
  });

  it("Strg+Shift+L wechselt zwischen hell und dunkel", async () => {
    const nutzer = userEvent.setup();
    render(<App />);
    await screen.findByRole("region", { name: "Jarvis" });

    expect(document.documentElement.classList.contains("dunkel")).toBe(false);
    await nutzer.keyboard("{Control>}{Shift>}L{/Shift}{/Control}");
    await waitFor(() => expect(document.documentElement.classList.contains("dunkel")).toBe(true));
  });

  it("F1 zeigt die Hilfe im Chat", async () => {
    const nutzer = userEvent.setup();
    render(<App />);
    await screen.findByRole("region", { name: "Jarvis" });

    await nutzer.keyboard("{F1}");
    expect(await screen.findByText(/Slash-Befehle im Chat/)).toBeInTheDocument();
  });

  it("ein geaendertes Kuerzel gilt sofort", async () => {
    const nutzer = userEvent.setup();
    render(<App />);
    await screen.findByRole("region", { name: "Jarvis" });

    useStore.getState().belegungSetzen("befehlspalette", { taste: "p", strg: true, shift: true });
    await nutzer.keyboard("{Control>}k{/Control}");
    expect(screen.queryByPlaceholderText(/Befehl, Modul oder Agent/)).not.toBeInTheDocument();

    await nutzer.keyboard("{Control>}{Shift>}P{/Shift}{/Control}");
    expect(await screen.findByPlaceholderText(/Befehl, Modul oder Agent/)).toBeInTheDocument();
  });
});

describe("Chat", () => {
  it("schickt eine Nachricht und zeigt die Antwort", async () => {
    const nutzer = userEvent.setup();
    render(<App />);
    const feld = await screen.findByLabelText("Nachricht an Jarvis");

    await nutzer.type(feld, "Hallo Jarvis");
    await nutzer.keyboard("{Enter}");

    expect(await screen.findByText("Hallo Jarvis")).toBeInTheDocument();
    expect(await screen.findByText(/Antwort vom Server/)).toBeInTheDocument();
    expect(FakeWebSocket.letzte?.gesendet[0]).toContain("Hallo Jarvis");
  });

  it("beantwortet /hilfe selbst, ohne den Server zu fragen", async () => {
    const nutzer = userEvent.setup();
    render(<App />);
    const feld = await screen.findByLabelText("Nachricht an Jarvis");

    await nutzer.type(feld, "/hilfe{Enter}");
    expect(await screen.findByText(/Slash-Befehle im Chat/)).toBeInTheDocument();
    expect(FakeWebSocket.letzte?.gesendet).toHaveLength(0);
  });

  it("schlaegt Slash-Befehle beim Tippen vor", async () => {
    const nutzer = userEvent.setup();
    render(<App />);
    const feld = await screen.findByLabelText("Nachricht an Jarvis");

    await nutzer.type(feld, "/o");
    expect(await screen.findByText("/opus")).toBeInTheDocument();
  });

  it("sagt ehrlich, wenn ein Befehl nicht existiert", async () => {
    const nutzer = userEvent.setup();
    render(<App />);
    const feld = await screen.findByLabelText("Nachricht an Jarvis");

    await nutzer.type(feld, "/fliegen{Enter}");
    expect(await screen.findByText(/kenne ich nicht/)).toBeInTheDocument();
  });

  it("Shift+Enter macht eine neue Zeile statt zu senden", async () => {
    const nutzer = userEvent.setup();
    render(<App />);
    const feld = await screen.findByLabelText("Nachricht an Jarvis");

    await nutzer.type(feld, "Zeile eins");
    await nutzer.keyboard("{Shift>}{Enter}{/Shift}");
    await nutzer.type(feld, "Zeile zwei");
    expect((feld as HTMLTextAreaElement).value).toContain("\n");
    expect(FakeWebSocket.letzte?.gesendet).toHaveLength(0);
  });
});

describe("Agents-Tab", () => {
  it("fragt vor dem Loeschen nach", async () => {
    const nutzer = userEvent.setup();
    render(<App />);
    await screen.findByText("Recherche");

    await nutzer.click(screen.getByLabelText("Agent Recherche loeschen"));
    const nachfrage = await screen.findByRole("alertdialog");
    expect(within(nachfrage).getByText(/wirklich loeschen/i)).toBeInTheDocument();

    // Abbrechen laesst den Agent stehen
    await nutzer.click(within(nachfrage).getByText("Abbrechen"));
    expect(screen.getByText("Recherche")).toBeInTheDocument();
  });

  it("loescht erst nach Bestaetigung", async () => {
    const nutzer = userEvent.setup();
    render(<App />);
    await screen.findByText("Recherche");

    await nutzer.click(screen.getByLabelText("Agent Recherche loeschen"));
    await nutzer.click(await screen.findByText("Loeschen"));
    await waitFor(() => expect(screen.queryByText("Recherche")).not.toBeInTheDocument());
  });
});

describe("Modulbaum", () => {
  it("ist ein echter Baum fuer Bedienhilfen", async () => {
    render(<App />);
    const baum = await screen.findByRole("tree", { name: "Modulbaum" });
    expect(within(baum).getAllByRole("treeitem").length).toBeGreaterThan(0);
  });

  it("laesst sich mit den Pfeiltasten bedienen", async () => {
    const nutzer = userEvent.setup();
    render(<App />);
    const baum = await screen.findByRole("tree", { name: "Modulbaum" });
    const eintraege = within(baum).getAllByRole("treeitem");

    eintraege[0]?.focus();
    expect(eintraege[0]).toHaveFocus();
    await nutzer.keyboard("{ArrowDown}");
    expect(eintraege[1]).toHaveFocus();
  });
});

describe("Fehlerfall", () => {
  it("erklaert ein abgelaufenes Token statt nur zu schweigen", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({ ok: false, status: 401, json: () => Promise.resolve({}) } as Response),
      ),
    );
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/Token/);
  });
});
