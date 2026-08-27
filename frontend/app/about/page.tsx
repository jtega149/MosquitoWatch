import { Brain, Database, LineChart, MessageSquareText, Shield } from "lucide-react";

const STEPS = [
  {
    title: "Collect Data",
    description: "Pull NYC Health trap detections and weather at ZIP centroids.",
    icon: Database,
  },
  {
    title: "Prepare & Analyze",
    description: "Join ZIP × week tables and engineer lagged weather features.",
    icon: LineChart,
  },
  {
    title: "Predict Risk",
    description: "Score elevated West Nile-positive mosquito activity by ZIP.",
    icon: Brain,
  },
  {
    title: "Explain with AI",
    description: "Gemini turns model outputs into a short plain-language brief.",
    icon: MessageSquareText,
  },
  {
    title: "Inform & Protect",
    description: "Residents see maps, trends, and prevention steps they can act on.",
    icon: Shield,
  },
];

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <section className="rounded-2xl border border-white/10 bg-[#131a2b] p-8">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-start">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-[#22c55e] text-3xl">
            🦟
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-white">About MosquitoWatch NYC</h1>
            <p className="mt-3 text-sm leading-relaxed text-slate-300">
              MosquitoWatch NYC is an AI-powered public-health dashboard that forecasts elevated West
              Nile-positive mosquito activity by ZIP code and week. It combines NYC Health surveillance
              with weather and seasonality signals so residents can see where activity is concentrated
              and what they can do about it.
            </p>
            <p className="mt-3 text-sm leading-relaxed text-slate-400">
              The product predicts mosquito / surveillance activity — not individual human infection
              risk. Map colors come from <code className="text-slate-300">GET /forecasts</code>. ZIP
              detail and Gemini copy come from <code className="text-slate-300">POST /predict</code>.
              Detection charts come from <code className="text-slate-300">{`GET /trends/{zip}`}</code>.
            </p>
          </div>
        </div>
      </section>

      <section>
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
          How it works
        </h2>
        <div className="grid gap-3 md:grid-cols-5">
          {STEPS.map((step, i) => (
            <article
              key={step.title}
              className="relative rounded-2xl border border-white/10 bg-[#131a2b] p-4"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#22c55e]/15 text-[#4ade80]">
                <step.icon className="h-5 w-5" />
              </div>
              <h3 className="mt-3 text-sm font-semibold text-white">{step.title}</h3>
              <p className="mt-1 text-xs leading-relaxed text-slate-400">{step.description}</p>
              {i < STEPS.length - 1 && (
                <div className="absolute -right-2 top-8 hidden text-[#22c55e] md:block">→</div>
              )}
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
