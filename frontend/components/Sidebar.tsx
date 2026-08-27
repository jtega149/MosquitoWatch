"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  Database,
  Droplets,
  LineChart,
  Map,
  Search,
} from "lucide-react";
import { DATA_UPDATED } from "@/lib/mock-data";

const NAV = [
  { href: "/", label: "Map Overview", icon: Map },
  { href: "/zip-lookup", label: "ZIP Lookup", icon: Search },
  { href: "/trends", label: "Trends", icon: LineChart },
  { href: "/prevention", label: "Prevention Tips", icon: Droplets },
  { href: "/data-sources", label: "Data Sources", icon: Database },
  { href: "/about", label: "About", icon: BookOpen },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-white/8 bg-[#0c1220]">
      <nav className="flex flex-1 flex-col gap-1 p-3 pt-6">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                active
                  ? "bg-[#22c55e]/15 text-[#4ade80]"
                  : "text-slate-400 hover:bg-white/5 hover:text-slate-100"
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-white/8 p-4 text-[11px] leading-relaxed text-slate-500">
        <div>
          Data updated: <span className="text-slate-300">{DATA_UPDATED}</span>
        </div>
        <div className="mt-2">© 2026 MosquitoWatch NYC</div>
      </div>
    </aside>
  );
}
