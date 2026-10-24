import { motion } from "framer-motion";
import { InfoTip } from "@/components/common/InfoTip";
import { AnimatedNumber } from "@/components/common/AnimatedNumber";
import { fmtNum } from "@/lib/format";

const RangeBar = ({ min, max, avg, value, decimals, label, testId }) => {
  const lo = Math.min(min, value) * 0.94;
  const hi = Math.max(max, value) * 1.04;
  const pct = (v) => `${((v - lo) / (hi - lo)) * 100}%`;
  return (
    <div className="mt-8" data-testid={testId}>
      <div className="flex justify-between text-[11px] text-[#202522]/45">
        <span>{label}</span>
        <span className="font-mono-num">
          {fmtNum(min, decimals)} – {fmtNum(max, decimals)}
        </span>
      </div>
      <div className="relative mt-2.5 h-1.5 rounded-full bg-[#183F32]/[0.07]">
        <div className="absolute inset-y-0 rounded-full bg-[#89A98C]/45" style={{ left: pct(min), width: `calc(${pct(max)} - ${pct(min)})` }} />
        <div className="absolute -top-1 h-3.5 w-px bg-[#C8A96B]" style={{ left: pct(avg) }} title="Average" />
        <motion.div
          className="absolute -top-[5px] h-4 w-4 -ml-2 rounded-full bg-[#183F32] ring-4 ring-white shadow"
          initial={false}
          animate={{ left: pct(value) }}
          transition={{ type: "spring", stiffness: 120, damping: 20 }}
        />
      </div>
      <div className="mt-2.5 flex items-center gap-4 text-[11px] text-[#202522]/45">
        <span className="inline-flex items-center gap-1.5"><span className="h-1.5 w-3 rounded-full bg-[#89A98C]/60" /> Prior-season range</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-3 w-px bg-[#C8A96B]" /> Average {fmtNum(avg, decimals)}</span>
      </div>
    </div>
  );
};

export const MetricCard = ({ testId, icon: Icon, title, detail, tooltip, value, decimals, unit, caption, badge, meta, range, delta, deltaLabel = "vs past avg", index = 0 }) => {
  return (
    <motion.article
      data-testid={testId}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: index * 0.08, ease: [0.22, 1, 0.36, 1] }}
      className="card-surface p-7 flex flex-col hover:-translate-y-0.5 transition-transform duration-300"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="h-10 w-10 rounded-2xl bg-[#183F32]/[0.06] text-[#183F32] grid place-items-center">
            <Icon size={18} strokeWidth={1.7} />
          </span>
          <div>
            <h3 className="text-[15px] font-semibold tracking-tight">{title}</h3>
            <p className="text-xs text-[#202522]/50">{detail}</p>
          </div>
        </div>
        <InfoTip text={tooltip} testId={`${testId}-tooltip`} label={`About ${title}`} />
      </div>
      <div className="mt-8 flex items-baseline gap-2">
        <AnimatedNumber value={value} decimals={decimals} testId={`${testId}-value`} className="font-mono-num text-5xl font-medium tracking-tighter text-[#202522]" />
        <span className="text-sm text-[#202522]/45">{unit}</span>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <p className="text-[13px] text-[#202522]/60">{caption}</p>
        {delta != null && (
          <span data-testid={`${testId}-delta`} className={`font-mono-num text-[11px] px-2 py-0.5 rounded-full ${delta >= 0 ? "bg-[#183F32]/[0.07] text-[#183F32]" : "bg-[#C8A96B]/15 text-[#7a5f2a]"}`}>
            {delta >= 0 ? "+" : ""}{fmtNum(delta, 1)}% {deltaLabel}
          </span>
        )}
      </div>
      {badge && <div className="mt-4" data-testid={`${testId}-badge`}>{badge}</div>}
      {range && range.min != null && <RangeBar {...range} value={value} decimals={decimals} testId={`${testId}-range`} />}
      <dl className="mt-auto pt-7 grid grid-cols-2 gap-4">
        {meta.map((m) => (
          <div key={m.label} className="pt-4 border-t border-[#183F32]/[0.08]">
            <dt className="text-[10.5px] uppercase tracking-[0.14em] text-[#202522]/40">{m.label}</dt>
            <dd className="mt-1 text-[13px] font-medium text-[#202522]" data-testid={m.testId}>{m.value}</dd>
          </div>
        ))}
      </dl>
    </motion.article>
  );
};
