import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/bricolage-grotesque";
import "@fontsource-variable/figtree";
import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/600.css";
import "./styles/tokens.css";
import "./styles/base.css";
import { App } from "./App";
import { demo } from "./api/demo";
import { backendDisponivel, live } from "./api/live";
import { AppProvider } from "./lib/app";

// Com o backend no ar, o app fala com o modelo; sem ele (ou com ?demo), roda o roteiro de demonstração.
async function iniciar() {
  const forcarDemo = new URLSearchParams(window.location.search).has("demo");
  const api = !forcarDemo && (await backendDisponivel()) ? live : demo;
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <AppProvider api={api}>
        <App />
      </AppProvider>
    </StrictMode>,
  );
}
iniciar();
