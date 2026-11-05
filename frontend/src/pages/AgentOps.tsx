// Author: Pradeep Sahoo — Retail Nexus AI
import { useQuery } from "@tanstack/react-query";
import { api } from "../services/api";
import { Badge, Card, ErrorBox, Loading, SectionTitle } from "../components/ui";

export default function AgentOps() {
  const q = useQuery({ queryKey: ["runs"], queryFn: () => api.runs() });
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorBox error={q.error as Error} />;
  const items = q.data?.items ?? [];
  return (
    <div className="space-y-4">
      <SectionTitle title="AI Operations · Agent Trace" sub="Every agent run is recorded with its steps, tool calls, provider, model and token accounting." />
      {items.length === 0 ? (
        <div className="rounded-md border border-dashed border-navy-700 p-6 text-center text-sm text-navy-200/70">
          No agent runs yet. Investigate an exception to produce one.
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((r: any) => (
            <Card key={r.run_id}>
              <div className="flex flex-wrap items-center gap-2">
                <div className="font-mono text-xs">{r.run_id}</div>
                <Badge kind={r.status === "SUCCEEDED" ? "LOW" : r.status === "FAILED" ? "CRITICAL" : "MEDIUM"}>{r.status}</Badge>
                <div className="text-xs text-navy-200/70">exception {r.exception_id}</div>
                <div className="text-xs text-navy-200/70">{r.provider}/{r.model}</div>
                <div className="text-xs text-navy-200/70">tokens in {r.tokens_in} · out {r.tokens_out}</div>
                <div className="text-xs text-navy-200/70">cost {r.cost_estimate_usd.toFixed(4)} USD</div>
                <div className="ml-auto text-xs text-navy-200/70">{new Date(r.started_at).toLocaleString()}</div>
              </div>
              {r.error && <div className="mt-2 rounded-md border border-rose-500/30 bg-rose-500/10 p-2 text-xs text-rose-200">{r.error}</div>}
              <div className="mt-2 grid gap-2 text-xs md:grid-cols-2">
                {(r.steps ?? []).map((s: any, i: number) => (
                  <div key={i} className="rounded border border-navy-800 bg-navy-900/70 p-2">
                    <div className="flex items-center justify-between">
                      <div className="font-semibold text-navy-100">{s.name}</div>
                      <Badge kind={s.status === "success" ? "LOW" : s.status === "error" ? "CRITICAL" : "MEDIUM"}>{s.status}</Badge>
                    </div>
                    {s.outputs?.rationale && <div className="mt-1 text-navy-200/80">{s.outputs.rationale}</div>}
                    {(s.tool_calls ?? []).map((t: any, j: number) => (
                      <div key={j} className="mt-1 rounded bg-navy-950 p-1 font-mono text-[11px] text-navy-200/80">
                        {t.name}({Object.keys(t.args).join(", ")}) {t.error ? "→ ERROR" : "→ ok"}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
