// Author: Pradeep Sahoo — Retail Nexus AI
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../services/api";
import { Badge, Button, Card, ErrorBox, Loading, SectionTitle, money, pct } from "../components/ui";

export default function Recommendations() {
  const qc = useQueryClient();
  const [status, setStatus] = useState("PENDING_APPROVAL");
  const q = useQuery({ queryKey: ["recommendations", status], queryFn: () => api.recommendations({ status, limit: 100 }) });
  const [note, setNote] = useState<Record<string, string>>({});

  const approve = useMutation({
    mutationFn: ({ id }: { id: string }) => api.approve(id, note[id]),
    onSuccess: () => qc.invalidateQueries(),
  });
  const reject = useMutation({
    mutationFn: ({ id }: { id: string }) => api.reject(id, note[id]),
    onSuccess: () => qc.invalidateQueries(),
  });
  const ask = useMutation({
    mutationFn: ({ id }: { id: string }) => api.requestEvidence(id, note[id]),
    onSuccess: () => qc.invalidateQueries(),
  });

  return (
    <div className="space-y-4">
      <SectionTitle
        title="Recommendation Center"
        sub="Ranked by priority and net benefit. Approvals route through the simulated action adapter."
        right={
          <select value={status} onChange={e => setStatus(e.target.value)} className="rounded-md border border-navy-700 bg-navy-900 px-3 py-1.5 text-sm">
            {["PENDING_APPROVAL", "EVIDENCE_REQUESTED", "APPROVED", "REJECTED", "EXECUTED"].map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        }
      />
      {q.isLoading ? <Loading /> : q.error ? <ErrorBox error={q.error as Error} /> : (
        <div className="space-y-3">
          {q.data.items.length === 0 && <div className="rounded-md border border-dashed border-navy-700 p-6 text-center text-sm text-navy-200/70">No recommendations in this bucket.</div>}
          {q.data.items.map((r: any) => (
            <Card key={r.recommendation_id}>
              <div className="flex flex-wrap items-center gap-2">
                <div className="font-mono text-xs text-navy-200/70">{r.recommendation_id}</div>
                <Badge kind={r.risk_tier}>{r.action_type}</Badge>
                <Badge>{r.priority}</Badge>
                <Badge>{r.status}</Badge>
                <div className="ml-auto text-xs text-navy-200/70">confidence {pct(r.confidence)}</div>
              </div>
              <div className="mt-2 text-sm text-navy-50">{r.business_rationale}</div>
              <div className="mt-2 grid gap-2 text-xs md:grid-cols-4">
                <Stat label="Revenue at risk" v={money(r.estimated_revenue_at_risk)} />
                <Stat label="Intervention cost" v={money(r.estimated_intervention_cost)} />
                <Stat label="Net benefit" v={money(r.estimated_net_benefit)} emph={r.estimated_net_benefit >= 0 ? "ok" : "crit"} />
                <Stat label="Risk tier" v={r.risk_tier} />
              </div>
              {r.assumptions?.length ? (
                <ul className="mt-2 list-disc pl-5 text-xs text-navy-200/70">
                  {r.assumptions.map((a: string, i: number) => <li key={i}>{a}</li>)}
                </ul>
              ) : null}
              {r.status === "PENDING_APPROVAL" || r.status === "EVIDENCE_REQUESTED" ? (
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <input className="flex-1 rounded-md border border-navy-700 bg-navy-900 px-3 py-1.5 text-sm" placeholder="Reviewer comment (optional)"
                         value={note[r.recommendation_id] ?? ""} onChange={e => setNote(n => ({ ...n, [r.recommendation_id]: e.target.value }))}/>
                  <Button kind="primary" onClick={() => approve.mutate({ id: r.recommendation_id })}>Approve</Button>
                  <Button kind="danger" onClick={() => reject.mutate({ id: r.recommendation_id })}>Reject</Button>
                  {r.status === "PENDING_APPROVAL" && <Button kind="secondary" onClick={() => ask.mutate({ id: r.recommendation_id })}>Request evidence</Button>}
                </div>
              ) : null}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function Stat({ label, v, emph }: { label: string; v: React.ReactNode; emph?: "ok" | "crit" }) {
  const c = emph === "ok" ? "text-emerald-300" : emph === "crit" ? "text-rose-300" : "text-navy-50";
  return (
    <div className="rounded-md border border-navy-800 bg-navy-900/50 p-2">
      <div className="text-[10px] uppercase tracking-wide text-navy-200/70">{label}</div>
      <div className={`mt-1 text-sm font-semibold tabular-nums ${c}`}>{v}</div>
    </div>
  );
}
