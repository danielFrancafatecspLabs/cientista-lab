// Markdown mínimo e seguro para as falas dos agentes: parágrafos, **negrito**,
// `código`, citações (>) e listas (- ou 1.). Sem HTML bruto.
import { Fragment, type ReactNode } from "react";

function inline(texto: string, chave: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let ultimo = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(texto))) {
    if (m.index > ultimo) out.push(texto.slice(ultimo, m.index));
    const t = m[0];
    out.push(t.startsWith("**") ? <strong key={`${chave}-${i++}`}>{t.slice(2, -2)}</strong> : <code key={`${chave}-${i++}`}>{t.slice(1, -1)}</code>);
    ultimo = m.index + t.length;
  }
  if (ultimo < texto.length) out.push(texto.slice(ultimo));
  return out;
}

export function Markdown({ texto }: { texto: string }) {
  const blocos = texto.replace(/\r/g, "").split(/\n{2,}/);
  return (
    <>
      {blocos.map((b, i) => {
        const linhas = b.split("\n");
        if (linhas.every((l) => l.startsWith(">"))) {
          return <blockquote key={i}>{inline(linhas.map((l) => l.replace(/^>\s?/, "")).join(" "), `q${i}`)}</blockquote>;
        }
        if (linhas.every((l) => /^\s*([-*]|\d+[.)])\s+/.test(l))) {
          const ordenada = /^\s*\d/.test(linhas[0]);
          const itens = linhas.map((l, j) => <li key={j}>{inline(l.replace(/^\s*([-*]|\d+[.)])\s+/, ""), `l${i}-${j}`)}</li>);
          return ordenada ? <ol key={i}>{itens}</ol> : <ul key={i}>{itens}</ul>;
        }
        return (
          <p key={i}>
            {linhas.map((l, j) => <Fragment key={j}>{j > 0 && <br />}{inline(l, `p${i}-${j}`)}</Fragment>)}
          </p>
        );
      })}
    </>
  );
}
