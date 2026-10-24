import { Database, Calculator, MapPinned, Gauge, Eye } from "lucide-react";
import { Reveal } from "@/components/common/Reveal";

const ITEMS = [
  { icon: Database, title: "Historical CIMIS weather observations", body: "Built around California’s public CIMIS station network.", status: "Connected" },
  { icon: Calculator, title: "Agricultural calculations", body: "Chill hours, Dynamic Model chill portions and base-50°F GDD.", status: "Connected" },
  { icon: MapPinned, title: "Location-based estimates", body: "Kriged estimates for orchards between stations.", status: "Prototype" },
  { icon: Gauge, title: "Forecast validation", body: "Forecasts will be compared against later observations.", status: "In progress" },
  { icon: Eye, title: "Transparent uncertainty", body: "Every projection is shown with its range — never a single false-precise number.", status: "By design" },
];

export const TechSection = () => (
  <section id="technology" className="scroll-mt-16 bg-[#F7F7F2] py-28 sm:py-36" data-testid="technology-section">
    <div className="mx-auto max-w-[1440px] px-5 sm:px-8">
      <div className="grid gap-10 lg:grid-cols-12">
        <Reveal className="lg:col-span-4">
          <p className="eyebrow text-[#183F32]/70">Technology</p>
          <h2 className="mt-5 text-4xl sm:text-5xl font-semibold tracking-tight leading-[1.05]">Built on science. Honest about limits.</h2>
          <p className="mt-6 text-[15px] text-[#202522]/60 leading-relaxed">
            OrchardIQ is an early prototype. We show what each part is, and how far along it is.
          </p>
        </Reveal>
        <div className="lg:col-span-8 grid gap-px bg-[#183F32]/10 rounded-[28px] overflow-hidden sm:grid-cols-2">
          {ITEMS.map((it, i) => (
            <Reveal key={it.title} delay={i * 0.06} className={`bg-[#F7F7F2] p-8 ${i === ITEMS.length - 1 ? "sm:col-span-2" : ""}`}>
              <div data-testid={`tech-item-${i}`}>
                <div className="flex items-center justify-between">
                  <it.icon size={20} strokeWidth={1.6} className="text-[#183F32]" />
                  <span className="text-[10.5px] uppercase tracking-[0.14em] rounded-full border border-[#183F32]/15 px-2.5 py-1 text-[#202522]/55">{it.status}</span>
                </div>
                <h3 className="mt-6 text-lg font-semibold tracking-tight">{it.title}</h3>
                <p className="mt-2 text-sm text-[#202522]/60 leading-relaxed">{it.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </div>
  </section>
);
