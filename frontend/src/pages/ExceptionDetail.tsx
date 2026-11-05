// Author: Pradeep Sahoo — Retail Nexus AI
import { useMemo } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../services/api";
import { Badge, Button, Card, ErrorBox, KV, Loading, SectionTitle, money, pct } from "../components/ui";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function ExceptionDetail() {
  const { id = "" } = useParams();
  const qc = useQueryClient();
  const exc = useQuery({ queryKey: ["exception", id], queryFn: () => api.exception(id) });
  const demand = useQuery({
    queryKey: ["demand", exc.data?.product_id, exc.data?.store_id],
    queryFn: () => api.demand(exc.data.product_id, exc.data.store_id, 14),
    enabled: !!exc.data?.product_id && !!exc.data?.store_id,
  });
  const investigate = useMutation({
    mutationFn: () => api.investigate(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["exception", id] }); qc.invalidateQueries({ queryKey: ["runs"] }); qc.invalidateQueries({ queryKey: ["recommendations"] }); },
  });
  const runs = useQuery({ queryKey: ["runs", id], queryFn: () => api.runs(id) });
  const recs = useQuery({ queryKey: ["recs-for", id], queryFn: () => api.recommendations({ exception_id: id }) });

  const chartData = useMemo(() => {
    if (!demand.data) return [];
    const forecast = new Map(demand.data.forecast.map((p: any) => [p.date, p.forecast_units]));
    const recent = demand.data.recent_sales.map((r: any) => ({ date: r.date, actual: r.units }));
    const future = demand.data.forecast.map((p: any) => ({ date: p.date, forecast: p.forecast_units }));
    return [...recent, ...future];
  }, [demand.data]);

  if (exc.isLoading) return <Loading />;
  if (exc.error) return <ErrorBox error={exc.error as Error} />;
  const e = exc.data;

  return (
    <div className="space-y-5">
      <SectionTitle
        title={`Exception ${e.exception_id}`}
        sub={e.category}
        right={
          <Button onClick={() => investigate.mutate()} disabled={investigate.isPending}>
            {investigate.isPending ? "Agents working…" : "Investigate with agents"}
          </Button>
        }
      />

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="md:col-span-1">
          <SectionTitle title="Exception" />
          <KV k="Severity" v={<Badge kind={e.severity}>{e.severity}</Badge>} />
          <KV k="Risk score" v={e.risk_score.toFixed(2)} />
          <KV k="Impact (est.)" v={money(e.estimated_impact_usd)} />
          <KV k="Product" v={e.product_id ?? "—"} />
          <KV k="Store" v={e.store_id ?? "—"} />
          <KV k="Supplier" v={e.supplier_id ?? "—"} />
          <KV k="Status" v={<Badge>{e.status}</Badge>} />
          <KV k="Detected" v={new Date(e.detected_at).toLocaleString()} />
          <KV k="Workflow hint" v={e.workflow_hint ?? "—"} />
        </Card>

        <Card className="md:col-span-2">
          <SectionTitle title="Demand trend vs forecast" />
          {demand.isLoading ? <Loading /> : demand.data ? (
            <div className="h-72">
              <ResponsiveContainer>
                <LineChart data={chartData}>
                  <CartesianGrid stroke="#1f2a44" />
                  <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
                  <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #243154" }} />
                  <Legend />
                  <Line dataKey="actual" stroke="#60a5fa" strokeWidth={2} dot={false} connectNulls />
                  <Line dataKey="forecast" stroke="#22d3ee" strokeWidth={2} strokeDasharray="4 2" dot={false} connectNulls />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : <div className="text-sm text-navy-200/70">No product-store context on this exception.</div>}
        </Card>
      </div>

      <Card>
        <SectionTitle title="Evidence" sub="Explicit values the engine computed to justify this exception." />
        <pre className="scrollbar-thin overflow-auto rounded-md border border-navy-800 bg-navy-950 p-3 text-xs">{JSON.stringify(e.evidence, null, 2)}</pre>
      </Card>

      <Card>
        <SectionTitle title="Agent runs" />
        {(runs.data?.items ?? []).length === 0 ? (
          <div className="text-sm text-navy-200/70">No agent run yet. Click "Investigate with agents".</div>
        ) : (
          <div className="space-y-3">
            {runs.data.items.map((r: any) => (
              <div key={r.run_id} className="rounded-md border border-navy-800 p-3">
                <div className="flex flex-wrap items-center gap-3">
                  <div className="font-mono text-xs">{r.run_id}</div>
                  <Badge kind={r.status === "SUCCEEDED" ? "LOW" : r.status === "FAILED" ? "CRITICAL" : "MEDIUM"}>{r.status}</Badge>
                  <div className="text-xs text-navy-200/70">{r.provider}/{r.model}</div>
                  <div className="text-xs text-navy-200/70">tokens in {r.tokens_in} · out {r.tokens_out}</div>
                  <div className="ml-auto text-xs text-navy-200/70">{new Date(r.started_at).toLocaleString()}</div>
                </div>
                <div className="mt-2 grid gap-2 text-xs md:grid-cols-2">
                  {(r.steps ?? []).map((s: any, i: number) => (
                    <div key={i} className="rounded border border-navy-800 bg-navy-900/70 p-2">
                      <div className="flex items-center justify-between">
                        <div className="font-semibold text-navy-100">{s.name}</div>
                        <Badge kind={s.status === "success" ? "LOW" : s.status === "error" ? "CRITICAL" : "MEDIUM"}>{s.status}</Badge>
                      </div>
                      {s.outputs?.rationale && <div className="mt-1 text-navy-200/80">{s.outputs.rationale}</div>}
                      {s.tool_calls?.length ? (
                        <div className="mt-1 text-navy-200/60">tools: {s.tool_calls.map((t: any) => t.name).join(", ")}</div>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card>
        <SectionTitle title="Recommendations" />
        {(recs.data?.items ?? []).length === 0 ? (
          <div className="text-sm text-navy-200/70">No recommendations yet.</div>
        ) : (
          <div className="space-y-3">
            {recs.data.items.map((r: any) => (
              <div key={r.recommendation_id} className="rounded-md border border-navy-800 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge kind={r.risk_tier}>{r.action_type}</Badge>
                  <Badge>{r.priority}</Badge>
                  <Badge>{r.status}</Badge>
                  <div className="ml-auto text-xs text-navy-200/70">confidence {pct(r.confidence)}</div>
                </div>
                <div className="mt-2 text-sm text-navy-100">{r.business_rationale}</div>
                <div className="mt-2 grid gap-2 text-xs md:grid-cols-3">
                  <KV k="Revenue at risk" v={money(r.estimated_revenue_at_risk)} />
                  <KV k="Intervention cost" v={money(r.estimated_intervention_cost)} />
                  <KV k="Net benefit" v={money(r.estimated_net_benefit)} />
                </div>
                {r.assumptions?.length ? (
                  <ul className="mt-2 list-disc pl-5 text-xs text-navy-200/70">
                    {r.assumptions.map((a: string, i: number) => <li key={i}>{a}</li>)}
                  </ul>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
