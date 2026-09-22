/**
 * Das Token darf nicht in der Adresszeile stehen bleiben - sonst landet es
 * im Verlauf, in Lesezeichen und auf Screenshots.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { chatAdresse, holeToken, uebernehmeTokenAusAdresse } from "./token";

describe("Token", () => {
  beforeEach(() => {
    sessionStorage.clear();
    window.history.replaceState({}, "", "/");
  });

  it("uebernimmt das Token aus der Adresse", () => {
    window.history.replaceState({}, "", "/?token=geheim123");
    uebernehmeTokenAusAdresse(window.location);
    expect(holeToken()).toBe("geheim123");
  });

  it("raeumt die Adresszeile danach auf", () => {
    window.history.replaceState({}, "", "/?token=geheim123");
    uebernehmeTokenAusAdresse(window.location);
    expect(window.location.search).not.toContain("token");
  });

  it("laesst andere Parameter in Ruhe", () => {
    window.history.replaceState({}, "", "/?token=abc&modul=schule");
    uebernehmeTokenAusAdresse(window.location);
    expect(window.location.search).toContain("modul=schule");
    expect(window.location.search).not.toContain("token");
  });

  it("tut ohne Token nichts", () => {
    uebernehmeTokenAusAdresse(window.location);
    expect(holeToken()).toBeNull();
  });

  it("baut die WebSocket-Adresse mit Token", () => {
    window.history.replaceState({}, "", "/?token=abc+def");
    uebernehmeTokenAusAdresse(window.location);
    const adresse = chatAdresse(window.location);
    expect(adresse).toContain("/ws/chat?token=");
    expect(adresse.startsWith("ws://")).toBe(true);
  });
});

describe("Token verschwindet wirklich aus dem Verlauf", () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    window.history.replaceState({}, "", "/");
  });

  it("benutzt replaceState und NICHT pushState", () => {
    // Der Unterschied ist der ganze Sinn der Sache: pushState wuerde einen
    // neuen Eintrag im Verlauf anlegen - das Token stuende dann weiterhin
    // im "Zurueck"-Verlauf des Browsers.
    const ersetzen = vi.spyOn(window.history, "replaceState");
    const anhaengen = vi.spyOn(window.history, "pushState");

    window.history.replaceState({}, "", "/?token=geheim123");
    ersetzen.mockClear();

    uebernehmeTokenAusAdresse(window.location);

    expect(ersetzen).toHaveBeenCalledTimes(1);
    expect(anhaengen).not.toHaveBeenCalled();
    expect(String(ersetzen.mock.calls[0]?.[2])).not.toContain("token");

    ersetzen.mockRestore();
    anhaengen.mockRestore();
  });

  it("legt das Token in den sessionStorage, nicht in den localStorage", () => {
    // localStorage wuerde das Token ueber das Schliessen des Browsers hinaus
    // aufbewahren - es gilt aber ohnehin nur bis zum naechsten Serverstart.
    window.history.replaceState({}, "", "/?token=geheim123");
    uebernehmeTokenAusAdresse(window.location);

    expect(sessionStorage.getItem("jarvis.token")).toBe("geheim123");
    expect(localStorage.getItem("jarvis.token")).toBeNull();
    expect(JSON.stringify(localStorage)).not.toContain("geheim123");
  });

  it("behaelt das Token, wenn die Seite spaeter ohne Token geladen wird", () => {
    window.history.replaceState({}, "", "/?token=geheim123");
    uebernehmeTokenAusAdresse(window.location);

    // Zweiter Aufruf, diesmal ohne Token in der Adresse (z. B. nach F5).
    uebernehmeTokenAusAdresse(window.location);
    expect(holeToken()).toBe("geheim123");
  });

  it("wirft die Anwendung nicht um, wenn der Speicher gesperrt ist", () => {
    // Im privaten Modus kann sessionStorage eine Ausnahme werfen.
    const speichern = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("Speicher gesperrt");
    });
    window.history.replaceState({}, "", "/?token=geheim123");

    expect(() => uebernehmeTokenAusAdresse(window.location)).not.toThrow();
    expect(window.location.search).not.toContain("token");

    speichern.mockRestore();
  });
});
