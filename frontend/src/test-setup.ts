import "@testing-library/jest-dom/vitest";

// jsdom (die Browser-Attrappe fuer Tests) kennt scrollIntoView nicht.
// Das ist eine Luecke der Testumgebung, kein Fehler der Anwendung -
// deshalb ersetzen wir es durch eine leere Funktion.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}

// Dasselbe fuer ResizeObserver, den die Befehlspalette (cmdk) benutzt.
if (!("ResizeObserver" in globalThis)) {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}
