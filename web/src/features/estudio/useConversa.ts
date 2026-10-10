// Transforma o fluxo de eventos do Cientista em estado de interface.
import { useCallback, useEffect, useReducer, useRef } from "react";
import type { CardKind, Estado, Evento, Porque } from "../../api/types";
import { useApp } from "../../lib/app";

export interface CardItem { kind: CardKind | "handoff"; data: any }
export interface Item {
  id: string; de: "cientista" | "pessoa" | "sistema"; texto: string; cards: CardItem[];
  porque?: Porque; aberto?: boolean; quebra?: boolean; erro?: boolean;
}
interface S {
  estado: Estado | null; itens: Item[]; chips: string[]; upload: { descricao: string; formatos: string[] } | null;
  ocupado: boolean; lendoDocumento: boolean; mudou: string[]; carregando: boolean; erroCarga: string | null;
}

type A =
  | { t: "carregado"; estado: Estado; transcricao: { de: "pessoa" | "cientista"; texto: string }[] }
  | { t: "erro_carga"; msg: string }
  | { t: "pessoa"; texto: string }
  | { t: "pensando" }
  | { t: "evento"; e: Evento };

let seq = 0;
const novoId = () => `i${++seq}`;

function atual(itens: Item[]): [Item[], Item] {
  const ult = itens[itens.length - 1];
  if (ult && ult.de === "cientista" && ult.aberto) return [itens.slice(0, -1), ult];
  return [itens, { id: novoId(), de: "cientista", texto: "", cards: [], aberto: true }];
}

function reducer(s: S, a: A): S {
  switch (a.t) {
    case "carregado":
      return { ...s, carregando: false, estado: a.estado,
        itens: a.transcricao.map((x) => ({ id: novoId(), de: x.de, texto: x.texto, cards: [] })) };
    case "erro_carga":
      return { ...s, carregando: false, erroCarga: a.msg };
    case "pensando":
      return { ...s, ocupado: true, itens: [...s.itens, { id: novoId(), de: "cientista", texto: "", cards: [], aberto: true }] };
    case "pessoa":
      return { ...s, ocupado: true, chips: [], upload: null, itens: [...s.itens, { id: novoId(), de: "pessoa", texto: a.texto, cards: [] }] };
    case "evento": {
      const e = a.e;
      switch (e.type) {
        case "text": {
          const [resto, it] = atual(s.itens);
          const texto = it.quebra && it.texto ? `${it.texto.trimEnd()}\n\n${e.delta.trimStart()}` : it.texto + e.delta;
          return { ...s, itens: [...resto, { ...it, texto, quebra: false }] };
        }
        case "retry": {
          const [resto, it] = atual(s.itens);
          return { ...s, itens: [...resto, { ...it, texto: "", cards: [] }] };
        }
        case "card": {
          const [resto, it] = atual(s.itens);
          return { ...s, itens: [...resto, { ...it, cards: [...it.cards, { kind: e.kind, data: e.data }], quebra: true }] };
        }
        case "handoff": {
          const [resto, it] = atual(s.itens);
          return { ...s, estado: s.estado && { ...s.estado, status: e.status, encaminhamento: e.destino },
            itens: [...resto, { ...it, cards: [...it.cards, { kind: "handoff", data: e }], quebra: true }] };
        }
        case "porque": {
          const [resto, it] = atual(s.itens);
          const { type: _t, ...p } = e;
          return { ...s, itens: [...resto, { ...it, porque: p, quebra: true }] };
        }
        case "mapa":
          return { ...s, estado: s.estado && { ...s.estado, mapa: e.mapa } };
        case "ficha":
          return { ...s, mudou: e.changed, estado: s.estado && { ...s.estado, ficha: e.ficha, pendencias: e.pendencias, ficha_gerada: e.gerada } };
        case "chips":
          return { ...s, chips: e.options };
        case "upload":
          return { ...s, upload: { descricao: e.descricao, formatos: e.formatos } };
        case "auto_ingestao":
          return { ...s, lendoDocumento: true };
        case "error":
          return { ...s, itens: [...s.itens.map((i) => ({ ...i, aberto: false })), { id: novoId(), de: "sistema", texto: e.message, cards: [], erro: true }] };
        case "done":
          return { ...s, ocupado: false, lendoDocumento: false, estado: e.state,
            itens: s.itens.filter((i) => !(i.de === "cientista" && !i.texto && !i.cards.length)).map((i) => ({ ...i, aberto: false })) };
        default:
          return s;
      }
    }
  }
}

export function useConversa(sid: string) {
  const { api } = useApp();
  const [s, dispatch] = useReducer(reducer, {
    estado: null, itens: [], chips: [], upload: null, ocupado: false, lendoDocumento: false, mudou: [], carregando: true, erroCarga: null,
  });
  const iniciado = useRef<string | null>(null);
  const on = useCallback((e: Evento) => dispatch({ t: "evento", e }), []);

  useEffect(() => {
    if (iniciado.current === sid) return;
    iniciado.current = sid;
    (async () => {
      try {
        const est = await api.sessao(sid);
        const transcricao = est.transcricao ?? [];
        dispatch({ t: "carregado", estado: est, transcricao });
        if (!transcricao.length && est.status === "conversa") {
          dispatch({ t: "pensando" });
          await api.iniciar(sid, on);
        }
      } catch (err) {
        dispatch({ t: "erro_carga", msg: (err as Error).message });
      }
    })();
  }, [api, sid, on]);

  const enviar = useCallback(async (texto: string) => {
    dispatch({ t: "pessoa", texto });
    await api.mensagem(sid, texto, on);
  }, [api, sid, on]);

  const anexar = useCallback(async (file: File) => {
    dispatch({ t: "pessoa", texto: `📎 ${file.name}` });
    await api.arquivo(sid, file, on);
  }, [api, sid, on]);

  const retomar = useCallback(async () => {
    dispatch({ t: "pessoa", texto: "Voltei para ajustar a ficha conforme a revisão do Lab." });
    await api.retomar(sid, on);
  }, [api, sid, on]);

  const recarregar = useCallback(async () => {
    const est = await api.sessao(sid);
    dispatch({ t: "evento", e: { type: "done", state: est } });
  }, [api, sid]);

  return { ...s, enviar, anexar, retomar, recarregar };
}
