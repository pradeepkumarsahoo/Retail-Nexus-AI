// Author: Pradeep Sahoo — Retail Nexus AI
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "../services/api";
import { Button, Card, ErrorBox, Loading, SectionTitle, money } from "../components/ui";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, Cell } from "recharts";

const SCENARIO_PRESETS: { name: string; params?: any }[] = [
  { name: "BASELINE" },
  { name: "EXPEDITE", params: { expedite_arrival_day: 2 } },
  { name: "TRANSFER", params: { transfer_units: 100, arrival_day: 1 } },
  { name: "SWITCH_SUPPLIER", params: { units: 200, alt_lead_time_days: 5 } },
  { name: "INCREASE_REPLENISHMENT", params: { extra_units: 150, arrival_day: 7 } },
];

export default function Simulator() {
  const list = useQuery({ queryKey: ["exceptions-sim"], queryFn: () => api.exceptions({ limit: 100 }) });
  const [exceptionId, setExceptionId] = useState<string>("");
  const [horizon, setHorizon] = useState(14);
  const [scenarios] = useState(SCENARIO_PRESETS);

  const run = useMutation({
    mutationFn: () => api.simulate({ exception_id: exceptionId, scenarios, horizon_days: horizon }),
  });

  const data = run.data?.outcomes.map((o: any) => ({
    scenario: o.scenario,
    "Revenue exposure": -Math.round(o.revenue_exposure_usd),
    "Intervention cost": -Math.round(o.intervention_cost_usd),
    "Net benefit": Math.round(o.net_benefit_usd),
  })) ?? [];

  const eligible = (list.data?.items ?? []).filter((e: any) => e.product_id && e.store_id);

  return (
    <div className="space-y-4">
      <SectionTitle title="Scenario Simulator" sub="Deterministic. Identical inputs produce identical outputs. All formulas are listed under each outcome." />
      <Card>
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1">
            <span className="text-[10px] uppercase tracking-wide text-navy-200/70">Exception</span>
            <select value={exceptionId} onChange={e => setExceptionId(e.target.value)} className="min-w-[280px] rounded-md border border-navy-700 bg-navy-900 px-3 py-1.5 text-sm">
              <option value="">— pick an exception —</option>
              {eligible.map((e: any) => (
                <option key={e.exception_id} value={e.exception_id}>
                  {e.exception_id} · {e.category} · {e.product_id}/{e.store_id}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[10px] uppercase tracking-wide text-navy-200/70">Horizon (days)</span>
            <input type="number" value={horizon} onChange={e => setHorizon(parseInt(e.target.value) || 14)} className="w-24 rounded-md border border-navy-700 bg-navy-900 px-3 py-1.5 text-sm" />
          </label>
          <Button onClick={() => run.mutate()} disabled={!exceptionId || run.isPending}>{run.isPending ? "Simulating…" : "Run simulation"}</Button>
        </div>
      </Card>

      {run.error && <ErrorBox error={run.error as Error} />}
      {run.data && (
        <>
          <Card>
            <SectionTitle title="Outcomes" sub={`Recommended: ${run.data.recommended_scenario}`} />
            <div className="h-80">
              <ResponsiveContainer>
                <BarChart data={data}>
                  <CartesianGrid stroke="#1f2a44" />
                  <XAxis dataKey="scenario" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #243154" }} />
                  <Bar dataKey="Net benefit">
                    {data.map((d: any, i: number) => (
                      <Cell key={i} fill={d["Net benefit"] >= 0 ? "#10b981" : "#ef4444"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {run.data.outcomes.map((o: any) => (
              <Card key={o.scenario}>
                <div className="flex items-center justify-between">
                  <div className="text-sm font-semibold">{o.scenario}</div>
                  <div className={`text-sm font-medium ${o.net_benefit_usd >= 0 ? "text-emerald-300" : "text-rose-300"}`}>{money(o.net_benefit_usd)}</div>
                </div>
                <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                  <Row k="Projected inventory" v={o.projected_inventory_units} />
                  <Row k="Expected stockout" v={o.expected_stockout_units} />
                  <Row k="Lost sales units" v={o.expected_lost_sales_units} />
                  <Row k="Revenue exposure" v={money(o.revenue_exposure_usd)} />
                  <Row k="Intervention cost" v={money(o.intervention_cost_usd)} />
                </div>
                <div className="mt-2">
                  <div className="text-[10px] uppercase tracking-wide text-navy-200/70">Assumptions</div>
                  <ul className="list-disc pl-5 text-xs text-navy-200/80">
                    {o.assumptions.map((a: string, i: number) => <li key={i}>{a}</li>)}
                  </ul>
                  {o.constraints.length > 0 && (
                    <>
                      <div className="mt-2 text-[10px] uppercase tracking-wide text-amber-300">Constraints</div>
                      <ul className="list-disc pl-5 text-xs text-amber-200/90">
                        {o.constraints.map((c: string, i: number) => <li key={i}>{c}</li>)}
                      </ul>
                    </>
                  )}
                </div>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex justify-between">
      <span className="text-navy-200/70">{k}</span>
      <span className="tabular-nums">{v}</span>
    </div>
  );
}
