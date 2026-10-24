import { Snowflake, Thermometer, Sun, Database, Layers, FlaskConical } from "lucide-react";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { Reveal } from "@/components/common/Reveal";
import { METRICS } from "@/config/metrics";
import { useDataMode } from "@/context/DataModeContext";

const items = (demo) => [
  { icon: Snowflake, title: "Chill Hours", body: `${METRICS.chillHours.tooltip} Counted from November 1.` },
  { icon: Thermometer, title: "Chill Portions", body: `${METRICS.chillPortions.tooltip} Counted from November 1.` },
  { icon: Sun, title: "Growing Degree Days", body: `${METRICS.gdd.tooltip} Counted from January 1.` },
  {
    icon: Database,
    title: "Data sources",
    body: demo
      ? "Demo mode: every value is generated illustrative data, not CIMIS readings."
      : "Hourly CIMIS observations from five Central Valley stations, served by the team's FastAPI backend. Unless live updates are on, data comes from the archived hourly file.",
  },
  {
    icon: Layers,
    title: "Custom locations",
    body: "Pins between stations are kriged from the five stations. Sites more than 35 km from a station are flagged as rough estimates.",
  },
  {
    icon: FlaskConical,
    title: "Prototype status",
    body: "The 7-day forecast blends a gradient-boosting model with persistence and climatology. Uncertainty ranges and 14-day forecasts are not yet provided.",
  },
];

export const AboutSection = () => {
  const { mode } = useDataMode();
  return (
    <>
      <SectionHeader eyebrow="About" title="How to read OrchardIQ." description="Plain-language definitions and the honest status of each part of this prototype." testId="about-header" />
      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3" data-testid="about-grid">
        {items(mode === "demo").map((it, i) => (
          <Reveal key={it.title} delay={i * 0.05} className="card-surface p-7">
            <it.icon size={20} strokeWidth={1.6} className="text-[#183F32]" />
            <h3 className="mt-5 text-base font-semibold tracking-tight">{it.title}</h3>
            <p className="mt-2 text-sm text-[#202522]/60 leading-relaxed">{it.body}</p>
          </Reveal>
        ))}
      </div>
      <p className="mt-8 text-xs text-[#202522]/45 max-w-3xl leading-relaxed" data-testid="about-disclaimer">
        OrchardIQ is a hackathon prototype developed for Reboot the Earth 2026 — UC Davis × United Nations. It is not an official UN or UC Davis product, and its outputs should not be used for operational decisions.
      </p>
    </>
  );
};
