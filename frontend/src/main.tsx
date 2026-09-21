import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./app/App";
import { uebernehmeTokenAusAdresse } from "./lib/token";
import "./index.css";

// Als Allererstes: Token aus der Adresse holen und die Adresse aufraeumen.
uebernehmeTokenAusAdresse();

const wurzel = document.getElementById("root");
if (!wurzel) throw new Error("Kein Element mit der id 'root' gefunden.");

createRoot(wurzel).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
