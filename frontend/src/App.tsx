// Author: Pradeep Sahoo — Retail Nexus AI
import { NavLink, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import clsx from "clsx";
import { api, setToken } from "./services/api";
import Dashboard from "./pages/Dashboard";
import Exceptions from "./pages/Exceptions";
import ExceptionDetail from "./pages/ExceptionDetail";
import Recommendations from "./pages/Recommendations";
import Simulator from "./pages/Simulator";
import Suppliers from "./pages/Suppliers";
import Demand from "./pages/Demand";
import AgentOps from "./pages/AgentOps";
import Login from "./pages/Login";

const NAV = [
  { to: "/", label: "Overview" },
  { to: "/exceptions", label: "Exceptions" },
  { to: "/recommendations", label: "Recommendations" },
  { to: "/simulator", label: "Simulator" },
  { to: "/suppliers", label: "Suppliers" },
  { to: "/demand", label: "Demand" },
  { to: "/agents", label: "AI Operations" },
];

function useUser() {
  const [u, setU] = useState<{ role?: string; display_name?: string; token?: string } | null>(() => {
    try { return JSON.parse(localStorage.getItem("ct_user") || "null"); } catch { return null; }
  });
  useEffect(() => {
    if (u?.token) setToken(u.token); else setToken(null);
    localStorage.setItem("ct_user", JSON.stringify(u ?? null));
  }, [u]);
  return [u, setU] as const;
}

export default function App() {
  const [user, setUser] = useUser();
  const nav = useNavigate();
  if (!user?.token) {
    return <Login onLogin={(u) => { setUser(u); nav("/"); }} />;
  }
  return (
    <div className="min-h-screen">
      <header className="border-b border-navy-800/70 bg-navy-950/90 backdrop-blur">
        <div className="mx-auto flex max-w-[1400px] items-center gap-6 px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-md bg-gradient-to-br from-accent-500 to-sky-500" />
            <div className="font-semibold tracking-tight">Retail Nexus AI</div>
            <span className="rounded-md border border-navy-700 bg-navy-900 px-2 py-0.5 text-[10px] uppercase tracking-wider text-navy-200">synthetic data</span>
          </div>
          <nav className="hidden flex-1 gap-1 md:flex">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.to === "/"}
                className={({ isActive }) => clsx(
                  "rounded-md px-3 py-1.5 text-sm",
                  isActive ? "bg-navy-800 text-navy-50" : "text-navy-200/80 hover:bg-navy-900 hover:text-navy-50"
                )}>
                {n.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3 text-sm">
            <div className="text-right">
              <div className="font-medium">{user.display_name}</div>
              <div className="text-xs text-navy-200/70">{user.role}</div>
            </div>
            <button
              onClick={() => { setUser(null); }}
              className="rounded-md border border-navy-700 px-2 py-1 text-xs text-navy-200/80 hover:bg-navy-800">
              Sign out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-[1400px] px-4 py-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/exceptions" element={<Exceptions />} />
          <Route path="/exceptions/:id" element={<ExceptionDetail />} />
          <Route path="/recommendations" element={<Recommendations />} />
          <Route path="/simulator" element={<Simulator />} />
          <Route path="/suppliers" element={<Suppliers />} />
          <Route path="/demand" element={<Demand />} />
          <Route path="/agents" element={<AgentOps />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  );
}
