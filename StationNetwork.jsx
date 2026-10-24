import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useInView } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { OrchardMap } from "@/components/OrchardMap";
import { STATIC_STATION_VMS, regionFor } from "@/data/stations";

export const StationNetwork = () => {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-120px" });
  const [hovered, setHovered] = useState(null);
  const navigate = useNavigate();
  const open = (id) => navigate(`/dashboard?station=${id}`);
  return (
    <section id="stations" ref={ref} className="scroll-mt-16 relative bg-[#0e1210] text-white" data-testid="stations-section">
      <div className="relative h-[88vh] min-h-[620px]">
        {inView ? (
          <div className="absolute inset-0">
            <OrchardMap className="h-full w-full" stations={STATIC_STATION_VMS} activeStationId={hovered} onStationSelect={open} showControls={false} testId="landing-map" />
          </div>
        ) : (
          <div className="absolute inset-0 bg-[#0e1210]" />
        )}
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-[#0e1210]/90 via-[#0e1210]/30 to-transparent z-[400]" />
        <div className="pointer-events-none absolute inset-x-0 top-10 sm:top-16 z-[600]">
        <div className="mx-auto max-w-[1440px] px-5 sm:px-8">
        <div className="pointer-events-auto sm:w-[380px]">
          <p className="eyebrow text-[#C8A96B]">Station network</p>
          <h2 className="mt-4 text-3xl sm:text-5xl font-semibold tracking-tight leading-tight">From the globe to your grove.</h2>
          <p className="mt-4 text-sm text-white/60 leading-relaxed">Five CIMIS weather stations across California’s Central Valley anchor the demo. Choose one to open its dashboard.</p>
          <ul className="mt-6 sm:mt-8 glass-dark rounded-3xl border border-white/10 divide-y divide-white/[0.07] overflow-hidden" data-testid="landing-station-list">
            {STATIC_STATION_VMS.map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  data-testid={`landing-station-${s.id}`}
                  onMouseEnter={() => setHovered(s.id)}
                  onMouseLeave={() => setHovered(null)}
                  onFocus={() => setHovered(s.id)}
                  onBlur={() => setHovered(null)}
                  onClick={() => open(s.id)}
                  className="group w-full flex items-center justify-between px-5 py-3.5 text-left hover:bg-white/[0.05] transition-colors"
                >
                  <span>
                    <span className="block text-[15px] font-medium font-display">{s.name}</span>
                    <span className="block text-xs text-white/45">{regionFor(s.id)} · CIMIS #{s.id}</span>
                  </span>
                  <ArrowRight size={16} className="text-white/30 group-hover:text-[#C8A96B] group-hover:translate-x-0.5 transition-all" />
                </button>
              </li>
            ))}
          </ul>
        </div>
        </div>
        </div>
      </div>
    </section>
  );
};
