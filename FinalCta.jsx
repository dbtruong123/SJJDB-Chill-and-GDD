import { Link } from "react-router-dom";
import { Reveal } from "@/components/common/Reveal";

export const FinalCta = () => (
  <section className="relative h-[90vh] min-h-[560px] overflow-hidden bg-[#141816]" data-testid="final-cta-section">
    <img src="/images/rows.jpg" alt="Orchard rows seen from above" loading="lazy" className="absolute inset-0 h-full w-full object-cover" />
    <div className="absolute inset-0 bg-black/45" />
    <div className="relative z-10 h-full mx-auto max-w-[1440px] px-5 sm:px-8 flex flex-col items-center justify-center text-center">
      <Reveal>
        <h2 className="text-4xl sm:text-6xl lg:text-7xl font-semibold tracking-tight text-white leading-[1.02] max-w-4xl">
          Know Your Orchard.
          <br />
          <span className="text-white/70">Plan With Confidence.</span>
        </h2>
      </Reveal>
      <Reveal delay={0.2}>
        <Link to="/dashboard" data-testid="final-cta-launch-btn" className="mt-12 inline-flex rounded-full bg-white text-[#183F32] px-10 py-4 text-sm font-semibold hover:bg-[#C8A96B] hover:text-white transition-colors duration-300">
          Launch Dashboard
        </Link>
      </Reveal>
    </div>
  </section>
);
