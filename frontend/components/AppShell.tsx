"use client";

import { ForecastProvider } from "@/lib/forecast-context";
import { ChatWidget } from "./ChatWidget";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <ForecastProvider>
      <div className="flex min-h-screen bg-[#0a0e1a] text-slate-100">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <Header />
          <main className="min-h-0 flex-1 overflow-auto p-5">{children}</main>
        </div>
      </div>
      <ChatWidget />
    </ForecastProvider>
  );
}
