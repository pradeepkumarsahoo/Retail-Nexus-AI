// Author: Pradeep Sahoo — Retail Nexus AI
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../services/api";
import { Button, Card, ErrorBox, Loading, SectionTitle, Stat, money } from "../components/ui";
import { BarChart, Bar, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis, PieChart, Pie, Cell } from "recharts";

const SEV_COLOR: Record<string, string> = { CRITICAL: "#ef4444", HIGH: "#f59e0b", MEDIUM: "#38bdf8", LOW: "#10b981" };
const CAT_COLORS = ["#22d3ee", "#60a5fa", "#a78bfa", "#f472b6", "#fbbf24", "#34d399", "#fb923c", "#f87171", "#8ab4f8", "#c084fc", "#2dd4bf"];

export default function Dashboard() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });
  const detect = useMutation({
    mutationFn: api.detect,
    onSuccess: () => qc.invalidateQueries(),
  });
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorBox error={q.error as Error} />;
  const d = q.data;
  const catData = Object.entries(d?.exceptions_by_category ?? {}).map(([name, value]) => ({ name, value }));
  return (
    <div className="space-y-6">
      <SectionTitle
        title="Retail Nexus AI — Executive Overview"
        sub="Live from the backend. All figures are computed from the loaded synthetic dataset."
        right={
          <Button onClick={() => detect.mutate()} disabled={detect.isPending}>
            {detect.isPending ? "Scanning…" : "Run exception sweep"}
          </Button>
        }
      />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <Stat label="Active exceptions" value={d.active_exceptions} />
        <Stat label="High or critical" value={d.high_or_critical} accent={d.high_or_critical > 0 ? "crit" : "default"} />
        <Stat label="Products at risk" value={d.products_at_stockout_risk} accent="warn" />
        <Stat label="Suppliers at risk" value={d.suppliers_at_risk} />
        <Stat label="Pending approvals" value={d.pending_approvals} />
        <Stat label="Revenue exposure" value={money(d.estimated_revenue_exposure_usd)} accent="crit" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <SectionTitle title="Exception trend (last 14 days)" sub="Count of detected exceptions by severity." />
          <div className="h-72">
            <ResponsiveContainer>
              <BarChart data={d.trend_last_14_days}>
                <CartesianGrid stroke="#1f2a44" />
                <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #243154" }} />
                <Legend />
                <Bar dataKey="CRITICAL" stackId="a" fill={SEV_COLOR.CRITICAL} />
                <Bar dataKey="HIGH" stackId="a" fill={SEV_COLOR.HIGH} />
                <Bar dataKey="MEDIUM" stackId="a" fill={SEV_COLOR.MEDIUM} />
                <Bar dataKey="LOW" stackId="a" fill={SEV_COLOR.LOW} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card>
          <SectionTitle title="Risk distribution by category" />
          <div className="flex h-72 items-center">
            <div className="h-full flex-1">
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={catData} dataKey="value" nameKey="name" innerRadius={60} outerRadius={95} paddingAngle={2}>
                    {catData.map((_, i) => <Cell key={i} fill={CAT_COLORS[i % CAT_COLORS.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #243154" }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="w-56 space-y-1 text-sm">
              {catData.map((c, i) => (
                <div key={c.name} className="flex items-center gap-2">
                  <span className="inline-block h-3 w-3 rounded-sm" style={{ background: CAT_COLORS[i % CAT_COLORS.length] }} />
                  <span className="flex-1 truncate text-navy-100">{c.name}</span>
                  <span className="tabular-nums text-navy-200/80">{c.value as number}</span>
                </div>
              ))}
              {catData.length === 0 && <div className="text-navy-200/60">No categories yet.</div>}
            </div>
          </div>
        </Card>
      </div>

      <Card>
        <SectionTitle title="Severity split" sub="Open, investigating, or recommendation-ready exceptions." />
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((s) => (
            <Stat key={s} label={s} value={d.exceptions_by_severity?.[s] ?? 0} accent={s === "CRITICAL" ? "crit" : s === "HIGH" ? "warn" : s === "LOW" ? "ok" : "default"} />
          ))}
        </div>
      </Card>
    </div>
  );
}
