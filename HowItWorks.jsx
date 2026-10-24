import { motion } from "framer-motion";
import { MapPin, LineChart, CloudSun } from "lucide-react";
import { Reveal } from "@/components/common/Reveal";

const STEPS = [
  { n: "01", icon: MapPin, title: "Choose Your Orchard", body: "Select a weather station or place a pin on a map." },
  { n: "02", icon: LineChart, title: "Explore Climate Intelligence", body: "View chill hours, chill portions, GDD, and historical comparisons." },
  { n: "03", icon: CloudSun, title: "Understand What’s Next", body: "Explore 7–14 day forecasts and their uncertainty." },
];

export const HowItWorks = () => (
  <section id="how" className="scroll-mt-16 bg-white py-28 sm:py-36" data-testid="how-it-works-section">
    <div className="mx-auto max-w-[1440px] px-5 sm:px-8">
      <Reveal className="max-w-2xl">
        <p className="eyebrow text-[#183F32]/70">How it works</p>
        <h2 className="mt-5 text-4xl sm:text-5xl font-semibold tracking-tight text-[#202522]">Three steps. One clear picture.</h2>
      </Reveal>
      <div className="relative mt-20">
        <motion.div
          className="hidden md:block absolute top-6 left-0 right-0 h-px bg-[#183F32]/15 origin-left"
          initial={{ scaleX: 0 }}
          whileInView={{ scaleX: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1] }}
        />
        <ol className="grid gap-14 md:grid-cols-3 md:gap-10">
          {STEPS.map((s, i) => (
            <Reveal as="li" key={s.n} delay={0.2 + i * 0.15} className="relative" >
              <div data-testid={`how-step-${s.n}`}>
                <span className="relative z-10 inline-grid h-12 w-12 place-items-center rounded-full bg-[#183F32] text-white">
                  <s.icon size={18} strokeWidth={1.7} />
                </span>
                <p className="mt-8 font-mono-num text-sm text-[#C8A96B]">{s.n}</p>
                <h3 className="mt-2 text-2xl font-semibold tracking-tight">{s.title}</h3>
                <p className="mt-3 text-[15px] text-[#202522]/60 leading-relaxed max-w-sm">{s.body}</p>
              </div>
            </Reveal>
          ))}
        </ol>
      </div>
    </div>
  </section>
);
