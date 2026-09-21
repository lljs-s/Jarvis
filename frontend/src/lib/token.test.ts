/**
 * Das Token darf nicht in der Adresszeile stehen bleiben - sonst landet es
 * im Verlauf, in Lesezeichen und auf Screenshots.
 */

import { beforeEach, describe, expect, it } from "vitest";
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
