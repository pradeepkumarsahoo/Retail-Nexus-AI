// Author: Pradeep Sahoo — Retail Nexus AI
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../services/api";
import { Badge, Card, ErrorBox, Loading, SectionTitle } from "../components/ui";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function Demand() {
  const products = useQuery({ queryKey: ["products"], queryFn: api.products });
  const stores = useQuery({ queryKey: ["stores"], queryFn: api.stores });
  const [pid, setPid] = useState<string>("");
  const [sid, setSid] = useState<string>("");
  const [horizon, setHorizon] = useState(14);

  useEffect(() => {
    if (!pid && products.data?.length) setPid(products.data[0].product_id);
    if (!sid && stores.data?.length) setSid(stores.data[0].store_id);
  }, [products.data, stores.data]);

  const forecast = useQuery({
    queryKey: ["demand", pid, sid, horizon],
    queryFn: () => api.demand(pid, sid, horizon),
    enabled: !!pid && !!sid,
  });
  const stockout = useQuery({
    queryKey: ["stockout", pid, sid, horizon],
    queryFn: () => api.stockoutRisk(pid, sid, horizon),
    enabled: !!pid && !!sid,
  });

  const chart = useMemo(() => {
    if (!forecast.data) return [];
    const recent = forecast.data.recent_sales.map((r: any) => ({ date: r.date, actual: r.units }));
    const future = forecast.data.forecast.map((p: any) => ({ date: p.date, forecast: p.forecast_units }));
    return [...recent, ...future];
  }, [forecast.data]);

  return (
    <div className="space-y-4">
      <SectionTitle title="Demand Intelligence" sub="Compare forecast against actual sales per product and store." />
      <Card>
        <div className="flex flex-wrap items-end gap-3">
          <Select label="Product" value={pid} onChange={setPid} options={(products.data ?? []).map((p: any) => ({ v: p.product_id, l: `${p.product_id} · ${p.name}` }))} />
          <Select label="Store" value={sid} onChange={setSid} options={(stores.data ?? []).map((s: any) => ({ v: s.store_id, l: `${s.store_id} · ${s.city}` }))} />
          <label className="flex flex-col gap-1">
            <span className="text-[10px] uppercase tracking-wide text-navy-200/70">Horizon (days)</span>
            <input type="number" value={horizon} onChange={e => setHorizon(parseInt(e.target.value) || 14)} className="w-24 rounded-md border border-navy-700 bg-navy-900 px-3 py-1.5 text-sm" />
          </label>
        </div>
      </Card>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <SectionTitle title="Forecast vs actual" sub={forecast.data ? `Model: ${forecast.data.model}` : ""} />
          {forecast.isLoading ? <Loading /> : forecast.error ? <ErrorBox error={forecast.error as Error} /> : (
            <div className="h-80">
              <ResponsiveContainer>
                <LineChart data={chart}>
                  <CartesianGrid stroke="#1f2a44" />
                  <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 11 }} tickFormatter={v => v.slice(5)} />
                  <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #243154" }} />
                  <Legend />
                  <Line dataKey="actual" stroke="#60a5fa" strokeWidth={2} dot={false} connectNulls />
                  <Line dataKey="forecast" stroke="#22d3ee" strokeWidth={2} strokeDasharray="4 2" dot={false} connectNulls />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
        <Card>
          <SectionTitle title="Stockout risk" sub={horizon + " day horizon"} />
          {stockout.isLoading ? <Loading /> : stockout.error ? <ErrorBox error={stockout.error as Error} /> : (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <div className="text-3xl font-semibold tabular-nums">{(stockout.data.probability * 100).toFixed(1)}%</div>
                <Badge kind={stockout.data.risk_category}>{stockout.data.risk_category}</Badge>
              </div>
              {stockout.data.predicted_stockout_date && (
                <div className="text-xs text-amber-300">Model projects stockout on {stockout.data.predicted_stockout_date} — this is a model estimate, not a guarantee.</div>
              )}
              <div className="mt-2 text-xs font-semibold uppercase tracking-wide text-navy-200/70">Contributing factors</div>
              <table className="w-full text-xs">
                <tbody>
                  {stockout.data.contributing_factors.map((f: any, i: number) => (
                    <tr key={i} className="border-t border-navy-800/70">
                      <td className="py-1 text-navy-200/80">{f.metric}</td>
                      <td className="py-1 text-right font-mono">{String(f.value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="pt-2 text-xs text-navy-200/70">Suggested action: <strong className="text-navy-50">{stockout.data.suggested_action}</strong></div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function Select({ label, value, onChange, options }: { label: string; value: string; onChange: (v: string) => void; options: { v: string; l: string }[] }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-wide text-navy-200/70">{label}</span>
      <select value={value} onChange={e => onChange(e.target.value)} className="min-w-[200px] rounded-md border border-navy-700 bg-navy-900 px-3 py-1.5 text-sm">
        {options.map(o => <option key={o.v} value={o.v}>{o.l}</option>)}
      </select>
    </label>
  );
}
