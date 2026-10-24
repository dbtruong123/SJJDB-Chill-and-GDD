import { fmtNum } from "@/lib/format";

export const ChartTooltipShell = ({ title, rows, footer }) => (
  <div className="rounded-2xl bg-[#202522]/95 text-[#F7F7F2] px-4 py-3 shadow-2xl min-w-[200px] backdrop-blur" data-testid="chart-tooltip">
    <p className="text-[11px] uppercase tracking-[0.16em] text-white/50">{title}</p>
    <div className="mt-2 space-y-1.5">
      {rows.map((r) => (
        <div key={r.label} className="flex items-center justify-between gap-6 text-[12.5px]">
          <span className="inline-flex items-center gap-2 text-white/75">
            <span className="h-2 w-2 rounded-full" style={{ background: r.color }} />
            {r.label}
          </span>
          <span className="font-mono-num">{r.value}</span>
        </div>
      ))}
    </div>
    {footer && <p className="mt-2.5 pt-2 border-t border-white/10 text-[10.5px] text-white/45">{footer}</p>}
  </div>
);

export const fmtRange = (range, d) => (range ? `${fmtNum(range[0], d)} – ${fmtNum(range[1], d)}` : "—");

export const LegendItem = ({ color, label, dashed, band }) => (
  <span className="inline-flex items-center gap-2 text-xs text-[#202522]/60">
    {band ? (
      <span className="h-3 w-5 rounded-sm" style={{ background: color }} />
    ) : (
      <span className="w-5 border-t-2" style={{ borderColor: color, borderStyle: dashed ? "dashed" : "solid" }} />
    )}
    {label}
  </span>
);
