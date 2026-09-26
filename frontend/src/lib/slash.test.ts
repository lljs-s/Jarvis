import { describe, expect, it } from "vitest";
import { hilfetext, SLASHBEFEHLE, vorschlaege, zerlege } from "./slash";

describe("zerlege", () => {
  it("erkennt normalen Text als keinen Befehl", () => {
    expect(zerlege("Wie ist das Wetter?").istBefehl).toBe(false);
  });

  it("erkennt /opus mit Aufgabe", () => {
    const ergebnis = zerlege("/opus Vergleiche diese zwei Ansaetze");
    expect(ergebnis.istBefehl).toBe(true);
    expect(ergebnis.id).toBe("opus");
    expect(ergebnis.rest).toBe("Vergleiche diese zwei Ansaetze");
  });

  it("erkennt einen Befehl ohne Rest", () => {
    expect(zerlege("/hilfe").id).toBe("hilfe");
    expect(zerlege("/hilfe").rest).toBe("");
  });

  it("ignoriert Gross- und Kleinschreibung", () => {
    expect(zerlege("/HILFE").id).toBe("hilfe");
  });

  it("meldet unbekannte Befehle, statt sie zu verschlucken", () => {
    const ergebnis = zerlege("/fliegen jetzt");
    expect(ergebnis.istBefehl).toBe(true);
    expect(ergebnis.id).toBeUndefined();
    expect(ergebnis.unbekannt).toBe("/fliegen");
  });

  it("behandelt einen Schraegstrich mitten im Text nicht als Befehl", () => {
    expect(zerlege("Der Pfad ist notizen/todo.txt").istBefehl).toBe(false);
  });
});

describe("vorschlaege", () => {
  it("schlaegt passende Befehle vor", () => {
    expect(vorschlaege("/o").map((b) => b.name)).toEqual(["/opus"]);
  });

  it("zeigt alle Befehle beim ersten Schraegstrich", () => {
    expect(vorschlaege("/")).toHaveLength(SLASHBEFEHLE.length);
  });

  it("hoert auf, sobald die Aufgabe beginnt", () => {
    expect(vorschlaege("/opus mach was")).toEqual([]);
  });

  it("schlaegt bei normalem Text nichts vor", () => {
    expect(vorschlaege("hallo")).toEqual([]);
  });
});

describe("hilfetext", () => {
  it("nennt jeden Befehl", () => {
    const text = hilfetext();
    for (const befehl of SLASHBEFEHLE) expect(text).toContain(befehl.name);
  });

  it("nennt die wichtigsten Tastenkuerzel", () => {
    expect(hilfetext()).toContain("Strg+K");
    expect(hilfetext()).toContain("Strg+J");
    expect(hilfetext()).toContain("F2");
    expect(hilfetext()).toContain("Strg+V");
  });
});
