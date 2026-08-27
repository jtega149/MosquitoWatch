import { ExternalLink } from "lucide-react";
import { DATA_SOURCES } from "@/lib/mock-data";

export default function DataSourcesPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <h1 className="text-2xl font-semibold text-white">Data Sources</h1>
      <p className="text-sm text-slate-400">
        The forecast will combine public surveillance and weather. The dashboard currently shows mock
        scores; source links below are the real feeds we plan to use.
      </p>
      {DATA_SOURCES.map((src) => (
        <article key={src.name} className="rounded-2xl border border-white/10 bg-[#131a2b] p-6">
          <div className="flex items-start justify-between gap-3">
            <h2 className="text-lg font-semibold text-white">{src.name}</h2>
            <a
              href={src.href}
              target="_blank"
              rel="noreferrer"
              className="text-[#4ade80] hover:underline"
              aria-label={`Open ${src.name}`}
            >
              <ExternalLink className="h-4 w-4" />
            </a>
          </div>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">{src.description}</p>
          <dl className="mt-4 grid gap-2 text-xs text-slate-400 sm:grid-cols-3">
            <div>
              <dt className="uppercase tracking-wider text-slate-500">Source</dt>
              <dd className="mt-1 text-slate-200">{src.source}</dd>
            </div>
            <div>
              <dt className="uppercase tracking-wider text-slate-500">Data type</dt>
              <dd className="mt-1 text-slate-200">{src.dataType}</dd>
            </div>
            <div>
              <dt className="uppercase tracking-wider text-slate-500">Frequency</dt>
              <dd className="mt-1 text-slate-200">{src.frequency}</dd>
            </div>
          </dl>
        </article>
      ))}
      <p className="pt-2 text-xs leading-relaxed text-slate-500">
        All listed sources are public. Models are intended to update weekly during mosquito season
        (May–October). Lack of detection in a ZIP does not mean virus is absent.
      </p>
    </div>
  );
}
