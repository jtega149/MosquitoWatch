"use client";

import dynamic from "next/dynamic";

const Map = dynamic(() => import("./NycChoroplethMap").then((m) => m.NycChoroplethMap), {
  ssr: false,
  loading: () => (
    <div className="flex h-full min-h-[560px] items-center justify-center rounded-2xl border border-white/10 bg-[#131a2b] text-sm text-slate-400">
      Loading map…
    </div>
  ),
});

export function NycMap() {
  return <Map />;
}
