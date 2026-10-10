import type { ReactNode, SVGProps } from "react";

type IconName =
  | "logo" | "chat" | "code" | "shield" | "chart" | "send" | "clip" | "check" | "x" | "arrow" | "back" | "spark"
  | "doc" | "download" | "sun" | "moon" | "info" | "chevron" | "search" | "flask" | "quote" | "map" | "kit" | "layers" | "clock" | "swap";

const P: Record<IconName, ReactNode> = {
  logo: <path d="M6 18V6l6 6 6-6v12" />,
  chat: <path d="M5 18l-1.5 3L8 19.5h9a3 3 0 003-3V7a3 3 0 00-3-3H7a3 3 0 00-3 3v9.5a3 3 0 001 2.2z" />,
  code: <><path d="M9 8l-4 4 4 4" /><path d="M15 8l4 4-4 4" /></>,
  shield: <><path d="M12 3l7 3v5c0 4.5-3 8.2-7 10-4-1.8-7-5.5-7-10V6z" /><path d="M9 12l2 2 4-4" /></>,
  chart: <><path d="M4 20V10" /><path d="M10 20V4" /><path d="M16 20v-7" /><path d="M22 20H2" /></>,
  send: <path d="M5 12h12M13 6l6 6-6 6" />,
  clip: <path d="M20 11.5l-7.8 7.8a5 5 0 01-7-7l8.5-8.5a3.3 3.3 0 014.7 4.7l-8.4 8.4a1.7 1.7 0 01-2.4-2.4l7.7-7.7" />,
  check: <path d="M5 12.5l4.5 4.5L19 7.5" />,
  x: <path d="M6 6l12 12M18 6L6 18" />,
  arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
  back: <path d="M19 12H5M11 6l-6 6 6 6" />,
  spark: <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M18 6l-2.5 2.5M8.5 15.5L6 18" />,
  doc: <><path d="M7 3h7l5 5v13H7z" /><path d="M14 3v5h5M10 13h6M10 17h6" /></>,
  download: <><path d="M12 4v11M7 10l5 5 5-5" /><path d="M5 20h14" /></>,
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>,
  moon: <path d="M20 14.5A8 8 0 019.5 4a8 8 0 1010.5 10.5z" />,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v6M12 7.5v.5" /></>,
  chevron: <path d="M9 6l6 6-6 6" />,
  search: <><circle cx="11" cy="11" r="6.5" /><path d="M16 16l4.5 4.5" /></>,
  flask: <><path d="M9 3h6M10 3v6L4.5 18.5A1.7 1.7 0 006 21h12a1.7 1.7 0 001.5-2.5L14 9V3" /><path d="M7.5 15h9" /></>,
  quote: <path d="M7 17c-2 0-3-1.5-3-3.5C4 10 6.5 7.5 9 7M17 17c-2 0-3-1.5-3-3.5 0-3.5 2.5-6 5-6.5" />,
  map: <><path d="M9 4L3 6.5v13.5L9 17.5l6 2.5 6-2.5V4l-6 2.5z" /><path d="M9 4v13.5M15 6.5V20" /></>,
  kit: <><path d="M3 8l9-5 9 5v8l-9 5-9-5z" /><path d="M3 8l9 5 9-5M12 13v8" /></>,
  layers: <><path d="M12 3l9 5-9 5-9-5z" /><path d="M3 13l9 5 9-5" /></>,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  swap: <><path d="M7 4L3 8l4 4M3 8h14" /><path d="M17 20l4-4-4-4M21 16H7" /></>,
};

export function Icon({ name, size = 18, ...rest }: { name: IconName; size?: number } & SVGProps<SVGSVGElement>) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...rest}>
      {P[name]}
    </svg>
  );
}

export function Badge({ children, tom = "", dot = false, title }: { children: ReactNode; tom?: string; dot?: boolean; title?: string }) {
  return <span className={`badge ${tom}`} title={title}>{dot && <span className="dot" />}{children}</span>;
}

export function Meter({ valor, max = 3, accent = false, rotulo }: { valor: number; max?: number; accent?: boolean; rotulo?: string }) {
  return (
    <span className={`meter${accent ? " accent" : ""}`} role="meter" aria-valuenow={valor} aria-valuemin={0} aria-valuemax={max} aria-label={rotulo}>
      {Array.from({ length: max }, (_, i) => <i key={i} className={i < valor ? "on" : ""} />)}
    </span>
  );
}

export function Ring({ valor, size = 44, stroke = 4, children }: { valor: number; size?: number; stroke?: number; children?: ReactNode }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  return (
    <span className="ring" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--line)" strokeWidth={stroke} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--accent)" strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - Math.min(1, Math.max(0, valor)))}
          transform={`rotate(-90 ${size / 2} ${size / 2})`} style={{ transition: "stroke-dashoffset .7s var(--ease)" }} />
      </svg>
      <span className="ring-label">{children}</span>
    </span>
  );
}

export function Tabs<T extends string>({ valor, onChange, itens }: {
  valor: T; onChange: (v: T) => void; itens: { id: T; rotulo: string; icone?: IconName; count?: number }[];
}) {
  return (
    <div className="tabs" role="tablist">
      {itens.map((it) => (
        <button key={it.id} role="tab" aria-selected={valor === it.id} onClick={() => onChange(it.id)}>
          {it.icone && <Icon name={it.icone} size={15} />}
          {it.rotulo}
          {it.count != null && <span className="count">{it.count}</span>}
        </button>
      ))}
    </div>
  );
}

export function Empty({ icone = "spark", titulo, children }: { icone?: IconName; titulo: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <Icon name={icone} size={26} />
      <h3>{titulo}</h3>
      {children && <p>{children}</p>}
    </div>
  );
}

export function Avatar({ nome, tom = "var(--ink)" }: { nome: string; tom?: string }) {
  const ini = nome.split(/[\s·]+/).filter(Boolean).slice(0, 2).map((p) => p[0]?.toUpperCase()).join("") || "?";
  return <span className="avatar" style={{ background: tom }}>{ini}</span>;
}
