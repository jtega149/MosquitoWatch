import { Droplets, Megaphone, Shirt, SprayCan, AppWindow } from "lucide-react";
import { PREVENTION_TIPS } from "@/lib/mock-data";

const ICONS = {
  droplets: Droplets,
  spray: SprayCan,
  shirt: Shirt,
  screen: AppWindow,
  megaphone: Megaphone,
};

export default function PreventionPage() {
  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="text-2xl font-semibold text-white">Prevention Tips</h1>
      <p className="mt-2 max-w-2xl text-sm text-slate-400">
        Practical steps residents can take during mosquito season. These tips are general public-health
        guidance, not a substitute for NYC Health advisories.
      </p>
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {PREVENTION_TIPS.map((tip) => {
          const Icon = ICONS[tip.icon];
          return (
            <article
              key={tip.title}
              className="rounded-2xl border border-white/10 bg-[#131a2b] p-6"
            >
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#22c55e]/15 text-[#4ade80]">
                <Icon className="h-5 w-5" />
              </div>
              <h2 className="mt-4 text-lg font-semibold text-white">{tip.title}</h2>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">{tip.description}</p>
            </article>
          );
        })}
      </div>
    </div>
  );
}
