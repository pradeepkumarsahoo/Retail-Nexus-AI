// Author: Pradeep Sahoo — Retail Nexus AI
import clsx from "clsx";
import { ReactNode } from "react";

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={clsx("rounded-xl border border-navy-800/80 bg-navy-900/70 p-4 shadow-sm", className)}>
      {children}
    </div>
  );
}

export function Stat({ label, value, hint, accent }: { label: string; value: ReactNode; hint?: string; accent?: "default" | "warn" | "crit" | "ok" }) {
  const col = accent === "crit" ? "text-rose-400" : accent === "warn" ? "text-amber-300" : accent === "ok" ? "text-emerald-400" : "text-accent";
  return (
    <Card>
      <div className="text-xs uppercase tracking-wide text-navy-200/70">{label}</div>
      <div className={clsx("mt-2 text-2xl font-semibold tabular-nums", col)}>{value}</div>
      {hint && <div className="mt-1 text-xs text-navy-200/60">{hint}</div>}
    </Card>
  );
}

const sevStyle: Record<string, string> = {
  CRITICAL: "bg-rose-500/15 text-rose-300 border-rose-500/30",
  HIGH: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  MEDIUM: "bg-sky-500/15 text-sky-300 border-sky-500/30",
  LOW: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  INFORMATIONAL: "bg-navy-500/15 text-navy-200 border-navy-500/30",
};

export function Badge({ children, kind }: { children: ReactNode; kind?: string }) {
  const style = kind && sevStyle[kind] ? sevStyle[kind] : "bg-navy-800/80 text-navy-100 border-navy-700";
  return (
    <span className={clsx("inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium", style)}>
      {children}
    </span>
  );
}

export function Button({ children, onClick, kind = "primary", size = "md", disabled, type = "button" }: {
  children: ReactNode; onClick?: () => void;
  kind?: "primary" | "secondary" | "ghost" | "danger"; size?: "sm" | "md";
  disabled?: boolean; type?: "button" | "submit";
}) {
  const base = "inline-flex items-center justify-center rounded-md font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent";
  const sz = size === "sm" ? "px-2.5 py-1 text-xs" : "px-3.5 py-1.5 text-sm";
  const variants: Record<string, string> = {
    primary: "bg-accent-500 text-navy-950 hover:bg-accent-600",
    secondary: "bg-navy-800 text-navy-50 hover:bg-navy-700 border border-navy-700",
    ghost: "bg-transparent text-navy-100 hover:bg-navy-800",
    danger: "bg-rose-500/20 text-rose-200 hover:bg-rose-500/30 border border-rose-500/30",
  };
  return (
    <button type={type} disabled={disabled} onClick={onClick} className={clsx(base, sz, variants[kind])}>
      {children}
    </button>
  );
}

export function SectionTitle({ title, sub, right }: { title: string; sub?: string; right?: ReactNode }) {
  return (
    <div className="mb-3 flex items-end justify-between gap-4">
      <div>
        <h2 className="text-lg font-semibold text-navy-50">{title}</h2>
        {sub && <p className="mt-0.5 text-sm text-navy-200/70">{sub}</p>}
      </div>
      {right}
    </div>
  );
}

export function Empty({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-dashed border-navy-700 p-6 text-center text-sm text-navy-200/70">
      {message}
    </div>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return <div className="animate-pulse text-sm text-navy-200/60">{label}</div>;
}

export function ErrorBox({ error }: { error: Error | null | undefined }) {
  if (!error) return null;
  return <div className="rounded-md border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-200">{error.message}</div>;
}

export function KV({ k, v }: { k: string; v: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-6 border-b border-navy-800/70 py-1.5 text-sm last:border-b-0">
      <span className="text-navy-200/70">{k}</span>
      <span className="text-right font-medium text-navy-50">{v}</span>
    </div>
  );
}

export function money(n: number) {
  return n.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

export function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}
