// Author: Pradeep Sahoo — Retail Nexus AI
import { useQuery } from "@tanstack/react-query";
import { api } from "../services/api";
import { Badge, Card, ErrorBox, Loading, SectionTitle, pct } from "../components/ui";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function Suppliers() {
  const q = useQuery({ queryKey: ["suppliers"], queryFn: api.suppliers });
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorBox error={q.error as Error} />;
  const data = q.data.map((s: any) => ({ name: s.name.split(" ")[0] + " " + s.name.split(" ")[1], otd: Math.round(s.on_time_delivery_pct * 100), lead: s.avg_lead_time_days }));

  return (
    <div className="space-y-4">
      <SectionTitle title="Supplier Intelligence" sub="Historical performance; lower OTD = higher delay risk." />
      <Card>
        <SectionTitle title="On-time delivery by supplier" />
        <div className="h-72">
          <ResponsiveContainer>
            <BarChart data={data}>
              <CartesianGrid stroke="#1f2a44" />
              <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <YAxis unit="%" tick={{ fill: "#94a3b8", fontSize: 11 }} domain={[0, 100]} />
              <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #243154" }} />
              <Bar dataKey="otd" fill="#22d3ee" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
      <Card className="overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-navy-900/70 text-left text-xs uppercase tracking-wide text-navy-200/70">
              <tr>
                <th className="px-3 py-2">Supplier</th>
                <th className="px-3 py-2 text-right">OTD</th>
                <th className="px-3 py-2 text-right">Avg lead (days)</th>
                <th className="px-3 py-2 text-right">Lead variance</th>
                <th className="px-3 py-2 text-right">Late / Total POs</th>
                <th className="px-3 py-2 text-right">Capacity/day</th>
                <th className="px-3 py-2">Risk</th>
              </tr>
            </thead>
            <tbody>
              {q.data.map((s: any) => {
                const kind = s.on_time_delivery_pct >= 0.9 ? "LOW" : s.on_time_delivery_pct >= 0.75 ? "MEDIUM" : "HIGH";
                return (
                  <tr key={s.supplier_id} className="border-t border-navy-800/60">
                    <td className="px-3 py-2">{s.name} <span className="ml-1 font-mono text-[10px] text-navy-200/70">{s.supplier_id}</span></td>
                    <td className="px-3 py-2 text-right tabular-nums">{pct(s.on_time_delivery_pct)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{s.avg_lead_time_days.toFixed(1)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{s.lead_time_variance.toFixed(1)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{s.late_po_count} / {s.total_po_count}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{s.capacity_units_per_day.toLocaleString()}</td>
                    <td className="px-3 py-2"><Badge kind={kind}>{kind}</Badge></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
