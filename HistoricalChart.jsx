import { useState } from "react";
import { ResponsiveContainer, ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine } from "recharts";
import { MapPinned } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { SegmentedControl } from "@/components/common/SegmentedControl";
import { ChartSkeleton, ErrorState } from "@/components/common/States";
import { ChartTooltipShell, LegendItem, fmtRange } from "@/components/dashboard/ChartParts";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { useHistoricalSeasons } from "@/hooks/useOrchardData";
import { useDataMode } from "@/context/DataModeContext";
import { METRICS, METRIC_OPTIONS } from "@/config/metrics";
import { fmtNum } from "@/lib/format";

const C = { current: "#183F32", forecast: "#C8A96B", tipCurrent: "#89A98C", avg: "#6f7d72", band: "rgba(137,169,140,0.22)", seasons: ["#9fb7a2", "#b4c4b6", "#c9d3ca", "#a3ab9f"] };

const HistTooltip = ({ active, payload, data, decimals }) => {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  const rows = [
    p.currentObserved != null && { label: `${data.currentLabel} · observed`, value: fmtNum(p.currentObserved, decimals), color: C.tipCurrent },
    p.currentForecast != null && p.currentObserved == null && { label: `${data.currentLabel} · forecast`, value: fmtNum(p.currentForecast, decimals), color: C.forecast },
    p.avg != null && { label: "Past-season average", value: fmtNum(p.avg, decimals), color: C.avg },
    p.range && { label: "Past-season range", value: fmtRange(p.range, decimals), color: "#89A98C" },
    ...data.priorLabels.map((l, k) => p[`s${k}`] != null && { label: l, value: fmtNum(p[`s${k}`], decimals), color: C.seasons[k] }),
  ].filter(Boolean);
  return <ChartTooltipShell title={`${p.label}${p.day != null ? ` · day ${p.day}` : ""}`} rows={rows} footer={data.units} />;
};

const HistChart = ({ data, metric, showSeasons }) => {
  const d = METRICS[metric].decimals;
  return (
    <ResponsiveContainer width="100%" height={400}>
      <ComposedChart data={data.points} margin={{ top: 10, right: 12, left: -6, bottom: 0 }}>
        <CartesianGrid stroke="#183F32" strokeOpacity={0.06} vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#202522", opacity: 0.45 }} tickLine={false} axisLine={false} interval={data.points.length > 200 ? 30 : 14} minTickGap={16} />
        <YAxis tick={{ fontSize: 11, fill: "#202522", opacity: 0.45 }} tickLine={false} axisLine={false} width={52} tickFormatter={(v) => fmtNum(v, 0)} />
        <Tooltip content={<HistTooltip data={data} decimals={d} />} cursor={{ stroke: "#183F32", strokeOpacity: 0.15 }} />
        <Area dataKey="range" stroke="none" fill={C.band} isAnimationActive={false} />
        {showSeasons && data.priorLabels.map((l, k) => <Line key={l} dataKey={`s${k}`} stroke={C.seasons[k]} strokeWidth={1.2} dot={false} isAnimationActive={false} />)}
        <Line dataKey="avg" stroke={C.avg} strokeWidth={1.8} strokeDasharray="5 5" dot={false} isAnimationActive={false} />
        <Line dataKey="currentObserved" stroke={C.current} strokeWidth={3} dot={false} connectNulls={false} animationDuration={900} />
        <Line dataKey="currentForecast" stroke={C.forecast} strokeWidth={3} strokeDasharray="4 3" dot={false} connectNulls={false} isAnimationActive={false} />
        {data.issueLabel && <ReferenceLine x={data.issueLabel} stroke="#C8A96B" strokeDasharray="3 3" label={{ value: data.issueLabel, position: "insideTopRight", fontSize: 11, fill: "#8a6d33" }} />}
      </ComposedChart>
    </ResponsiveContainer>
  );
};

const UnsupportedForCustom = () => (
  <div className="flex flex-col sm:flex-row sm:items-center gap-5 py-10" data-testid="historical-unsupported">
    <span className="h-12 w-12 shrink-0 rounded-2xl bg-[#183F32]/[0.06] text-[#183F32] grid place-items-center">
      <MapPinned size={20} strokeWidth={1.7} />
    </span>
    <div>
      <h3 className="text-lg font-semibold">Season history is available for the five CIMIS stations only</h3>
      <p className="mt-1 text-sm text-[#202522]/60 max-w-2xl">
        The backend's point estimate gives this site's season-to-date, past-season average and 7-day forecast, but not a day-by-day season record. Select a station to compare full seasons.
      </p>
    </div>
  </div>
);

export const HistoricalChart = ({ selection }) => {
  const { mode } = useDataMode();
  const [metric, setMetric] = useState("chillPortions");
  const [showSeasons, setShowSeasons] = useState(true);
  const unsupported = mode === "live" && selection.type === "custom";
  const { data, isLoading, isError, error, refetch, isFetching } = useHistoricalSeasons(selection, metric);
  return (
    <>
      <SectionHeader
        eyebrow="Historical trends"
        title="This season against the last four."
        description="Running season totals aligned by day of season, with the past-season minimum–maximum range shaded behind them."
        testId="historical-header"
        actions={<SegmentedControl label="Historical metric" layoutId="hist-metric" testIdPrefix="historical-metric" value={metric} onChange={setMetric} options={METRIC_OPTIONS} />}
      />
      <div className="card-surface p-5 sm:p-8" data-testid="historical-chart-card">
        {unsupported ? (
          <UnsupportedForCustom />
        ) : (
          <>
            <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
              <div className="flex flex-wrap items-center gap-x-5 gap-y-2" data-testid="historical-legend">
                <LegendItem color={C.current} label={`${data?.currentLabel || "Current"} observed`} />
                {mode === "live" && <LegendItem color={C.forecast} label="7-day forecast" dashed />}
                <LegendItem color={C.avg} label="Past-season average" dashed />
                <LegendItem color={C.band} label="Past-season min–max" band />
                {showSeasons && <LegendItem color={C.seasons[0]} label="Past seasons" />}
              </div>
              <label className="inline-flex items-center gap-2.5 text-xs text-[#202522]/60 cursor-pointer">
                <Switch checked={showSeasons} onCheckedChange={setShowSeasons} data-testid="historical-seasons-toggle" />
                Individual seasons
              </label>
            </div>
            {isLoading && <ChartSkeleton testId="historical-chart-loading" />}
            {isError && <ErrorState testId="historical-error" title="Couldn't load season history" message={error?.message} onAction={refetch} />}
            {data && !isError && (
              <div className={`transition-opacity duration-300 ${isFetching ? "opacity-60" : "opacity-100"}`} data-testid="historical-chart">
                <HistChart data={data} metric={metric} showSeasons={showSeasons} />
                <p className="mt-4 text-xs text-[#202522]/50 leading-relaxed" data-testid="historical-note">{data.note}</p>
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
};
