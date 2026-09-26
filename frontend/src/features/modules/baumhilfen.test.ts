import { describe, expect, it } from "vitest";
import { knoten, wurzel } from "../../test-daten";
import { bereicheBisTiefe, eltern, finde, waehlbareStufen, zielBereich } from "./baumhilfen";

const MODUL = knoten({ id: "mod_1", name: "Mathe", art: "modul" });
const KAPUTT = knoten({ id: "ord_kaputt", name: "Kaputt", fehler: "kaputt", datenschutz: "lokal" });
const SCHULE = knoten({ id: "ord_schule", name: "Schule", kinder: [MODUL, KAPUTT] });
const BAUM = wurzel([SCHULE]);

describe("baumhilfen", () => {
  it("findet Knoten und Eltern", () => {
    expect(finde(BAUM, "mod_1")?.name).toBe("Mathe");
    expect(finde(BAUM, "gibtsnicht")).toBeNull();
    expect(eltern(BAUM, "mod_1")?.id).toBe("ord_schule");
    expect(eltern(BAUM, "ord_schule")?.id).toBe("wurzel");
  });

  it("Neues landet im gewaehlten Bereich, bei einem Modul in dessen Bereich", () => {
    expect(zielBereich(BAUM, "ord_schule")?.id).toBe("ord_schule");
    expect(zielBereich(BAUM, "mod_1")?.id).toBe("ord_schule");
    expect(zielBereich(BAUM, null)?.id).toBe("wurzel");
  });

  it("nie in einen fehlerhaften Bereich", () => {
    expect(zielBereich(BAUM, "ord_kaputt")?.id).toBe("ord_schule");
  });

  it("bietet keine Stufe unter der geerbten an", () => {
    expect(waehlbareStufen(knoten({ id: "a", name: "a", datenschutz_mindest: "offen" }))).toEqual([
      "offen",
      "vertraulich",
      "lokal",
    ]);
    expect(
      waehlbareStufen(knoten({ id: "b", name: "b", datenschutz_mindest: "vertraulich" })),
    ).toEqual(["vertraulich", "lokal"]);
  });

  it("klappt beim Start nur Bereiche auf", () => {
    expect(bereicheBisTiefe(BAUM.kinder, 1)).toEqual(["ord_schule"]);
    expect(bereicheBisTiefe(BAUM.kinder, 2)).toEqual(["ord_schule", "ord_kaputt"]);
  });
});
