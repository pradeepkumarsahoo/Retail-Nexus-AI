// Author: Pradeep Sahoo — Retail Nexus AI
import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../services/api";
import { Badge, Card, ErrorBox, Loading, SectionTitle, money } from "../components/ui";

const CATS = ["", "STOCKOUT_RISK", "LOW_DAYS_OF_SUPPLY", "DEMAND_SPIKE", "DEMAND_DECLINE", "SUPPLIER_DELAY", "EXCESS_INVENTORY", "AGING_INVENTORY"];
const SEV = ["", "CRITICAL", "HIGH", "MEDIUM", "LOW"];

export default function Exceptions() {
  const [filters, setFilters] = useState<Record<string, string>>({ status: "" });
  const q = useQuery({
    queryKey: ["exceptions", filters],
    queryFn: () => api.exceptions({ ...filters, limit: 100 }),
  });
  if (q.error) return <ErrorBox error={q.error as Error} />;
  return (
    <div className="space-y-4">
      <SectionTitle title="Exception Management" sub="Filter and triage. Click to investigate." />
      <Card>
        <div className="flex flex-wrap gap-3">
          <Field label="Category">
            <select value={filters.category ?? ""} onChange={(e) => setFilters(f => ({ ...f, category: e.target.value }))} className="input">
              {CATS.map(c => <option key={c} value={c}>{c || "— any —"}</option>)}
            </select>
          </Field>
          <Field label="Severity">
            <select value={filters.severity ?? ""} onChange={(e) => setFilters(f => ({ ...f, severity: e.target.value }))} className="input">
              {SEV.map(s => <option key={s} value={s}>{s || "— any —"}</option>)}
            </select>
          </Field>
          <Field label="Status">
            <select value={filters.status ?? ""} onChange={(e) => setFilters(f => ({ ...f, status: e.target.value }))} className="input">
              {["", "OPEN", "INVESTIGATING", "RECOMMENDATION_READY", "RESOLVED"].map(s => <option key={s} value={s}>{s || "— any —"}</option>)}
            </select>
          </Field>
          <Field label="Product">
            <input placeholder="P0001" value={filters.product_id ?? ""} onChange={(e) => setFilters(f => ({ ...f, product_id: e.target.value }))} className="input" />
          </Field>
          <Field label="Store">
            <input placeholder="S001" value={filters.store_id ?? ""} onChange={(e) => setFilters(f => ({ ...f, store_id: e.target.value }))} className="input" />
          </Field>
          <Field label="Min risk">
            <input placeholder="0.5" value={filters.min_risk ?? ""} onChange={(e) => setFilters(f => ({ ...f, min_risk: e.target.value }))} className="input" />
          </Field>
        </div>
      </Card>

      <Card className="overflow-hidden p-0">
        {q.isLoading ? (
          <div className="p-6"><Loading /></div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-navy-900/70 text-left text-xs uppercase tracking-wide text-navy-200/70">
                <tr>
                  <th className="px-3 py-2">ID</th>
                  <th className="px-3 py-2">Category</th>
                  <th className="px-3 py-2">Severity</th>
                  <th className="px-3 py-2">Product</th>
                  <th className="px-3 py-2">Store</th>
                  <th className="px-3 py-2">Supplier</th>
                  <th className="px-3 py-2 text-right">Risk</th>
                  <th className="px-3 py-2 text-right">Impact</th>
                  <th className="px-3 py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {q.data.items.map((e: any) => (
                  <tr key={e.exception_id} className="border-t border-navy-800/60 hover:bg-navy-900/50">
                    <td className="px-3 py-2 font-mono text-xs">
                      <Link to={`/exceptions/${e.exception_id}`} className="text-accent hover:underline">{e.exception_id}</Link>
                    </td>
                    <td className="px-3 py-2">{e.category}</td>
                    <td className="px-3 py-2"><Badge kind={e.severity}>{e.severity}</Badge></td>
                    <td className="px-3 py-2 font-mono text-xs">{e.product_id ?? "—"}</td>
                    <td className="px-3 py-2 font-mono text-xs">{e.store_id ?? "—"}</td>
                    <td className="px-3 py-2 font-mono text-xs">{e.supplier_id ?? "—"}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{Number(e.risk_score).toFixed(2)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{money(e.estimated_impact_usd)}</td>
                    <td className="px-3 py-2"><Badge>{e.status}</Badge></td>
                  </tr>
                ))}
                {q.data.items.length === 0 && (
                  <tr><td colSpan={9} className="p-6 text-center text-navy-200/60">No exceptions match your filters. Run the exception sweep from the dashboard.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      <style>{`.input { background: #0f172a; border: 1px solid #243154; color: #e6edf7; border-radius: 6px; padding: 4px 8px; font-size: 13px; }`}</style>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-wide text-navy-200/70">{label}</span>
      {children}
    </label>
  );
}
