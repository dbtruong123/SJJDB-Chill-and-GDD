import { Reveal } from "@/components/common/Reveal";
import { FeatureCard } from "@/components/landing/FeatureCard";

const FEATURES = [
  { image: "/images/field.jpg", title: "Understand Winter Chill", body: "Track chill hours and chill portions accumulated during the season." },
  { image: "/images/rows.jpg", title: "Measure Growing-Season Heat", body: "Monitor growing degree days to understand heat accumulation." },
  { image: "/images/path.jpg", title: "Look Ahead", body: "Explore short-term accumulation forecasts and uncertainty estimates." },
];

export const IntroSection = () => (
  <section id="intro" className="scroll-mt-16 bg-[#F7F7F2] py-28 sm:py-36" data-testid="intro-section">
    <div className="mx-auto max-w-[1440px] px-5 sm:px-8">
      <div className="grid gap-10 lg:grid-cols-12 items-end">
        <Reveal className="lg:col-span-7">
          <p className="eyebrow text-[#183F32]/70">The challenge</p>
          <h2 className="mt-5 text-4xl sm:text-5xl lg:text-6xl font-semibold tracking-tight leading-[1.04] text-[#202522]">
            Every orchard has its own climate.
          </h2>
        </Reveal>
        <Reveal delay={0.15} className="lg:col-span-5">
          <p className="text-base sm:text-lg text-[#202522]/65 leading-relaxed">
            Regional weather stations don’t always capture the conditions experienced by individual orchards. OrchardIQ brings together historical weather observations, agricultural models, and location-based estimates to make orchard climate information more accessible.
          </p>
        </Reveal>
      </div>
      <div className="mt-20 grid gap-5 md:grid-cols-3">
        {FEATURES.map((f, i) => (
          <FeatureCard key={f.title} {...f} index={i} testId={`feature-card-${i}`} />
        ))}
      </div>
    </div>
  </section>
);
