import { motion } from "framer-motion";

export const SegmentedControl = ({ options, value, onChange, testIdPrefix, layoutId, label, dark = false }) => (
  <div
    role="radiogroup"
    aria-label={label}
    className={`inline-flex max-w-full overflow-x-auto p-1 rounded-full border ${
      dark ? "bg-white/[0.06] border-white/10" : "bg-[#183F32]/[0.06] border-[#183F32]/[0.08]"
    }`}
  >
    {options.map((o) => {
      const active = o.value === value;
      const idle = dark ? "text-white/60 hover:text-white" : "text-[#202522]/55 hover:text-[#202522]";
      return (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={active}
          aria-disabled={o.disabled || undefined}
          disabled={o.disabled}
          title={o.title}
          data-testid={`${testIdPrefix}-${o.value}`}
          onClick={() => onChange(o.value)}
          className={`relative whitespace-nowrap px-4 py-1.5 text-[13px] font-medium rounded-full transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-45 ${
            active ? "text-[#183F32]" : idle
          }`}
        >
          {active && (
            <motion.span
              layoutId={layoutId}
              className="absolute inset-0 rounded-full bg-white shadow-[0_1px_3px_rgba(24,63,50,0.15)]"
              transition={{ type: "spring", stiffness: 420, damping: 34 }}
            />
          )}
          <span className="relative">{o.label}</span>
          {o.badge && <span className="relative ml-1.5 text-[9.5px] uppercase tracking-wider rounded-full border border-current px-1.5 py-px">{o.badge}</span>}
        </button>
      );
    })}
  </div>
);
