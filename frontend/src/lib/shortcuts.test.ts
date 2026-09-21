/**
 * Tests fuer die Tastenkuerzel.
 *
 * Die Pruefung ist eine reine Funktion - deshalb brauchen diese Tests
 * weder Browser noch Oberflaeche und laufen in Millisekunden.
 */

import { describe, expect, it, beforeEach } from "vitest";
import {
  AKTIONEN,
  alsText,
  ausEreignis,
  findeAktion,
  ladeBelegung,
  passt,
  speichereBelegung,
  standardBelegung,
} from "./shortcuts";

function taste(key: string, extras: Partial<KeyboardEvent> = {}) {
  return {
    key,
    ctrlKey: false,
    metaKey: false,
    shiftKey: false,
    altKey: false,
    ...extras,
  } as KeyboardEvent;
}

describe("passt", () => {
  it("erkennt Strg+K", () => {
    expect(passt(taste("k", { ctrlKey: true }), { taste: "k", strg: true })).toBe(true);
  });

  it("unterscheidet Gross- und Kleinschreibung nicht", () => {
    expect(passt(taste("K", { ctrlKey: true }), { taste: "k", strg: true })).toBe(true);
  });

  it("verlangt die Strg-Taste wirklich", () => {
    expect(passt(taste("k"), { taste: "k", strg: true })).toBe(false);
  });

  it("akzeptiert die Befehlstaste des Mac als Strg", () => {
    expect(passt(taste("k", { metaKey: true }), { taste: "k", strg: true })).toBe(true);
  });

  it("laesst zusaetzliche Modifikatoren nicht durchgehen", () => {
    // Strg+Shift+K ist NICHT Strg+K - sonst waeren Kuerzel nicht eindeutig.
    expect(passt(taste("k", { ctrlKey: true, shiftKey: true }), { taste: "k", strg: true })).toBe(
      false,
    );
  });
});

describe("findeAktion", () => {
  const belegung = standardBelegung();

  it("findet die Befehlspalette bei Strg+K", () => {
    expect(findeAktion(taste("k", { ctrlKey: true }), belegung)).toBe("befehlspalette");
  });

  it("findet das Chatfeld bei Strg+J", () => {
    expect(findeAktion(taste("j", { ctrlKey: true }), belegung)).toBe("chatFokus");
  });

  it("findet die Hilfe bei F1", () => {
    expect(findeAktion(taste("F1"), belegung)).toBe("hilfe");
  });

  it("gibt bei unbelegten Tasten nichts zurueck", () => {
    expect(findeAktion(taste("x"), belegung)).toBeUndefined();
  });

  it("beachtet eine geaenderte Belegung", () => {
    const eigene = { ...belegung, befehlspalette: { taste: "p", strg: true, shift: true } };
    expect(findeAktion(taste("k", { ctrlKey: true }), eigene)).toBeUndefined();
    expect(findeAktion(taste("p", { ctrlKey: true, shiftKey: true }), eigene)).toBe(
      "befehlspalette",
    );
  });
});

describe("Anzeige und Aufnahme", () => {
  it("schreibt Kombinationen lesbar", () => {
    expect(alsText({ taste: "k", strg: true })).toBe("Strg+K");
    expect(alsText({ taste: "l", strg: true, shift: true })).toBe("Strg+Shift+L");
    expect(alsText({ taste: "F1" })).toBe("F1");
  });

  it("liest einen Tastendruck als Kombination", () => {
    expect(ausEreignis(taste("k", { ctrlKey: true }))).toEqual({
      taste: "k",
      strg: true,
      shift: false,
      alt: false,
    });
  });

  it("ignoriert reine Modifikatortasten", () => {
    // Sonst waere "Strg" allein ein gueltiges Kuerzel.
    expect(ausEreignis(taste("Control", { ctrlKey: true }))).toBeUndefined();
    expect(ausEreignis(taste("Shift", { shiftKey: true }))).toBeUndefined();
  });
});

describe("Speichern", () => {
  beforeEach(() => localStorage.clear());

  it("gibt ohne gespeicherte Daten die Standards zurueck", () => {
    expect(ladeBelegung()).toEqual(standardBelegung());
  });

  it("merkt sich geaenderte Kuerzel", () => {
    const eigene = { ...standardBelegung(), chatFokus: { taste: "m", strg: true } };
    speichereBelegung(eigene);
    expect(ladeBelegung().chatFokus).toEqual({ taste: "m", strg: true });
  });

  it("ueberlebt kaputte gespeicherte Daten", () => {
    localStorage.setItem("jarvis.tastenbelegung", "{kein json");
    expect(ladeBelegung()).toEqual(standardBelegung());
  });

  it("ergaenzt fehlende Eintraege mit Standards", () => {
    // Wichtig nach einem Update, das eine neue Aktion mitbringt.
    localStorage.setItem("jarvis.tastenbelegung", JSON.stringify({ hilfe: { taste: "F2" } }));
    const belegung = ladeBelegung();
    expect(belegung.hilfe).toEqual({ taste: "F2" });
    expect(belegung.befehlspalette).toEqual({ taste: "k", strg: true });
  });
});

describe("Vollstaendigkeit", () => {
  it("jede Aktion hat einen Titel und eine Erklaerung", () => {
    for (const aktion of AKTIONEN) {
      expect(aktion.titel.length).toBeGreaterThan(3);
      expect(aktion.beschreibung.length).toBeGreaterThan(10);
    }
  });

  it("keine Kombination ist doppelt belegt", () => {
    const texte = AKTIONEN.map((a) => alsText(a.standard));
    expect(new Set(texte).size).toBe(texte.length);
  });
});
