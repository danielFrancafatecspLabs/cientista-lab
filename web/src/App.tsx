import { Shell } from "./components/Shell";
import { useApp } from "./lib/app";
import { Bancada } from "./features/bancada/Bancada";
import { Entrada } from "./features/entrada/Entrada";
import { Estudio } from "./features/estudio/Estudio";
import { Lab } from "./features/lab/Lab";
import { Sponsor } from "./features/sponsor/Sponsor";

export function App() {
  const { rota } = useApp();
  return (
    <Shell>
      {rota.tela === "entrada" && <Entrada papel={rota.papel} />}
      {rota.tela === "estudio" && <Estudio key={rota.sid} sid={rota.sid} />}
      {rota.tela === "bancada" && <Bancada key={rota.sid} sid={rota.sid} />}
      {rota.tela === "lab" && <Lab id={rota.id} />}
      {rota.tela === "sponsor" && <Sponsor id={rota.id} />}
    </Shell>
  );
}
