import { ResponsiveContainer, ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ReferenceArea } from "recharts";
import { ChartTooltipShell, fmtRange } from "@/components/dashboard/ChartParts";
import { METRICS } from "@/config/metrics";
import { fmtNum } from "@/lib/format";

export const FC = { observed: "#183F32", forecast: "#C8A96B", band: "rgba(200,169,107,0.22)" };

const FcTooltip = ({ active, payload, decimals, units, demo }) => {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  const rows = [
    p.observed != null && { label: "Observed season-to-date", value: fmtNum(p.observed, decimals), color: FC.observed },
    p.anchor && p.observed == null && { label: "Season-to-date", value: fmtNum(p.forecast, decimals), color: FC.observed },
    p.lead && { label: "Forecast season-to-date", value: fmtNum(p.forecast, decimals), color: FC.forecast },
    p.daily != null && { label: "Forecast for this day", value: fmtNum(p.daily, 2), color: "#e3d3ae" },
    p.lead && p.range && { label: "Illustrative range", value: fmtRange(p.range, decimals), color: "#e3d3ae" },
  ].filter(Boolean);
  const footer = p.lead ? `Day +${p.lead}${demo ? " · mock forecast" : ` · ${units}`}` : demo ? "Illustrative" : units;
  return <ChartTooltipShell title={p.label} rows={rows} footer={footer} />;
};

export const ForecastChart = ({ f, metric, units, demo }) => {
  const d = METRICS[metric].decimals;
  const lead8 = f.points.find((p) => p.lead === 8);
  const last = f.points[f.points.length - 1];
  const vals = f.points.flatMap((p) => [p.observed, p.forecast, ...(p.range || [])]).filter((v) => v != null);
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  const pad = Math.max((hi - lo) * 0.15, metric === "chillPortions" ? 0.2 : 2);
  const domain = [Math.max(0, Math.floor((lo - pad) * 10) / 10), Math.ceil((hi + pad) * 10) / 10];
  return (
    <ResponsiveContainer width="100%" height={380}>
      <ComposedChart data={f.points} margin={{ top: 24, right: 12, left: -6, bottom: 0 }}>
        <CartesianGrid stroke="#183F32" strokeOpacity={0.06} vertical={false} />
        {lead8 && <ReferenceArea x1={lead8.label} x2={last.label} fill="#183F32" fillOpacity={0.035} label={{ value: "Days 8–14 · climatology-weighted", position: "insideTop", fontSize: 11, fill: "#202522", opacity: 0.5 }} />}
        <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#202522", opacity: 0.45 }} tickLine={false} axisLine={false} interval="preserveStartEnd" minTickGap={18} />
        <YAxis domain={domain} tick={{ fontSize: 11, fill: "#202522", opacity: 0.45 }} tickLine={false} axisLine={false} width={56} tickFormatter={(v) => fmtNum(v, metric === "chillPortions" ? 1 : 0)} />
        <Tooltip content={<FcTooltip decimals={d} units={units} demo={demo} />} cursor={{ stroke: "#183F32", strokeOpacity: 0.15 }} />
        {demo && <Area dataKey="range" stroke="none" fill={FC.band} isAnimationActive={false} connectNulls={false} />}
        <Line dataKey="observed" stroke={FC.observed} strokeWidth={3} dot={false} isAnimationActive={false} />
        <Line dataKey="forecast" stroke={FC.forecast} strokeWidth={2.5} strokeDasharray="6 5" dot={{ r: 3, fill: FC.forecast, strokeWidth: 0 }} animationDuration={700} />
        <ReferenceLine x={f.issueLabel} stroke="#183F32" strokeOpacity={0.5} label={{ value: `Last observed · ${f.issueLabel}`, position: "top", fontSize: 11, fill: "#183F32" }} />
      </ComposedChart>
    </ResponsiveContainer>
  );
};
