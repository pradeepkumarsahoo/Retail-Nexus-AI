// Author: Pradeep Sahoo — Retail Nexus AI
import { useState } from "react";
import { api } from "../services/api";
import { Button, Card, ErrorBox } from "../components/ui";

const DEMO_USERS = [
  { user: "demo-director", role: "Supply Chain Director", pwd: "demo" },
  { user: "demo-procurement", role: "Procurement", pwd: "demo" },
  { user: "demo-manager", role: "Store Manager", pwd: "demo" },
  { user: "demo-analyst", role: "Analyst", pwd: "demo" },
  { user: "demo-admin", role: "Admin", pwd: "demo" },
];

export default function Login({ onLogin }: { onLogin: (u: { token: string; role: string; display_name: string }) => void }) {
  const [username, setUsername] = useState("demo-director");
  const [password, setPassword] = useState("demo");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<Error | null>(null);
  const submit = async () => {
    setErr(null); setBusy(true);
    try {
      const r = await api.login(username, password);
      onLogin({ token: r.access_token, role: r.role, display_name: r.display_name });
    } catch (e: any) { setErr(e); } finally { setBusy(false); }
  };
  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <div className="mb-4 flex items-center gap-2">
          <div className="h-7 w-7 rounded-md bg-gradient-to-br from-accent-500 to-sky-500" />
          <div className="text-lg font-semibold">Retail Nexus AI</div>
        </div>
        <p className="mb-5 text-sm text-navy-200/70">Dev credentials — any role below with password <code className="rounded bg-navy-800 px-1">demo</code>.</p>
        <label className="mb-2 block text-xs font-medium uppercase tracking-wide text-navy-200/70">Username</label>
        <input value={username} onChange={e => setUsername(e.target.value)}
               className="mb-3 w-full rounded-md border border-navy-700 bg-navy-900 px-3 py-2 text-sm" />
        <label className="mb-2 block text-xs font-medium uppercase tracking-wide text-navy-200/70">Password</label>
        <input type="password" value={password} onChange={e => setPassword(e.target.value)}
               className="mb-3 w-full rounded-md border border-navy-700 bg-navy-900 px-3 py-2 text-sm" />
        <ErrorBox error={err} />
        <div className="mt-4 flex items-center justify-between">
          <div className="flex flex-wrap gap-1">
            {DEMO_USERS.map(d => (
              <button key={d.user} onClick={() => { setUsername(d.user); setPassword("demo"); }}
                      className="rounded border border-navy-700 bg-navy-900 px-2 py-0.5 text-[11px] text-navy-200/80 hover:bg-navy-800">
                {d.role}
              </button>
            ))}
          </div>
          <Button onClick={submit} disabled={busy}>{busy ? "Signing in…" : "Sign in"}</Button>
        </div>
      </Card>
    </div>
  );
}
