import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Em desenvolvimento, /api vai para o backend FastAPI (python -m metaexp servir).
export default defineConfig({
  plugins: [react()],
  // fs.allow: o modo demonstração importa o catálogo de metaexp/catalogo/toolbox.json (fonte única).
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8000" }, fs: { allow: [".."] } },
  build: { outDir: "dist", sourcemap: false },
});
