import { useState } from "react";
import { Info } from "lucide-react";
import { SegmentedControl } from "@/components/common/SegmentedControl";
import { ChartSkeleton, ErrorState } from "@/components/common/States";
import { LegendItem } from "@/components/dashboard/ChartParts";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { ForecastChart, FC } from "@/components/dashboard/ForecastChart";
import { useForecastRows, useHistoricalSeasons, useDemoForecast } from "@/hooks/useOrchardData";
import { useDataMode } from "@/context/DataModeContext";
import { buildLiveForecast } from "@/services/forecastModel";
import { METRIC_KEYS } from "@/services/orchardApiService";
import { METRICS, METRIC_OPTIONS } from "@/config/metrics";
import { fmtNum } from "@/lib/format";

const SummaryTile = ({ metricKey, f, active, onClick, horizon, units }) => {
  const m = METRICS[metricKey];
  const sub = active ? "text-white/60" : "text-[#202522]/50";
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      data-testid={`forecast-summary-${metricKey}`}
      className={`text-left rounded-3xl p-6 border transition-all duration-300 ${
        active ? "bg-[#183F32] border-[#183F32] text-white shadow-[0_20px_40px_-20px_rgba(24,63,50,0.6)]" : "bg-white border-[#183F32]/[0.08] hover:border-[#183F32]/25"
      }`}
    >
      <p className={`text-[11px] uppercase tracking-[0.16em] ${active ? "text-white/55" : "text-[#202522]/45"}`}>{m.label}</p>
      <p className="mt-4 font-mono-num text-3xl font-medium tracking-tight" data-testid={`forecast-summary-${metricKey}-projected`}>
        {fmtNum(f.projected, m.decimals)} <span className={`text-sm ${active ? "text-white/50" : "text-[#202522]/40"}`}>{units}</span>
      </p>
      <p className={`mt-1 text-xs ${active ? "text-[#C8A96B]" : "text-[#183F32]"}`} data-testid={`forecast-summary-${metricKey}-added`}>
        +{fmtNum(f.added, 2)} projected over {horizon} days
      </p>
      <p className={`mt-4 text-xs font-mono-num ${sub}`}>
        {f.low != null ? `Range ${fmtNum(f.low, m.decimals)} – ${fmtNum(f.high, m.decimals)} (illustrative)` : `Normal for these days: ${f.normalNext7 != null ? `+${fmtNum(f.normalNext7, 2)}` : "—"}`}
      </p>
    </button>
  );
};

const DailyStrip = ({ days, metric, units }) => (
  <div className="mt-6" data-testid="forecast-daily-strip">
    <p className="text-[10.5px] uppercase tracking-[0.14em] text-[#202522]/45">Daily forecast · {METRICS[metric].label} ({units})</p>
    <div className="mt-3 grid grid-cols-4 sm:grid-cols-7 gap-2">
      {days.slice(0, 7).map((d) => (
        <div key={d.date} className="rounded-2xl bg-[#183F32]/[0.04] px-3 py-3" data-testid={`forecast-day-${d.horizon}`}>
          <p className="text-[11px] text-[#202522]/50">{d.label}</p>
          <p className="mt-1 font-mono-num text-[15px] font-medium" data-testid={`forecast-day-${d.horizon}-value`}>{fmtNum(d.value, 2)}</p>
          <p className="text-[10px] text-[#202522]/35">Day +{d.horizon}</p>
        </div>
      ))}
    </div>
  </div>
);

const useLiveForecast = (selection, summary, metric) => {
  const station = selection.type === "station";
  const rows = useForecastRows(selection);
  const seasons = useHistoricalSeasons(selection, metric);
  const isLoading = summary.isLoading || (station && rows.isLoading);
  const isError = summary.isError || (station && rows.isError);
  let vm = null;
  if (!isLoading && !isError && summary.data && (!station || (rows.data && !rows.isPlaceholderData))) {
    const s = station && seasons.data && !seasons.isPlaceholderData && seasons.data.metric === metric ? seasons.data : null;
    vm = Object.fromEntries(METRIC_KEYS.map((m) => [m, buildLiveForecast({ summary: summary.data, rows: station ? rows.data : null, seasons: m === metric ? s : null, metric: m })]));
  }
  return { vm, isLoading: isLoading || (!vm && !isError), isError, error: rows.error || summary.error, refetch: () => (station ? rows.refetch() : summary.refetch()), isFetching: rows.isFetching };
};

const Notes = ({ demo }) => (
  <div className="mt-5 flex gap-3 text-xs text-[#202522]/55 leading-relaxed" data-testid="forecast-uncertainty-note">
    <Info size={15} className="shrink-0 mt-0.5 text-[#183F32]/60" />
    {demo ? (
      <p>Days 8–14 rely more heavily on climatology, so the band widens. <strong className="font-semibold text-[#202522]/75">All demo forecast values and ranges are illustrative mock data.</strong></p>
    ) : (
      <p>
        Each day blends the team's gradient-boosting model with persistence and climatology; later days lean more on normals. The backend returns one best estimate per day and no uncertainty bounds, so no band is drawn. A 14-day forecast is not available yet.
      </p>
    )}
  </div>
);

export const ForecastSection = ({ selection, summary }) => {
  const { mode } = useDataMode();
  const demo = mode === "demo";
  const [horizon, setHorizon] = useState("7");
  const [metric, setMetric] = useState("gdd");
  const live = useLiveForecast(selection, summary, metric);
  const demoQ = useDemoForecast(selection, Number(horizon));
  const q = demo ? { vm: demoQ.data?.metrics, ...demoQ } : live;
  const effHorizon = demo ? horizon : "7";
  const units = (m) => summary.data?.metrics[m]?.units || METRICS[m].unit;
  const options = [
    { value: "7", label: "Next 7 days" },
    demo ? { value: "14", label: "Next 14 days" } : { value: "14", label: "Next 14 days", disabled: true, badge: "Coming soon", title: "The backend provides 7-day forecasts only" },
  ];
  return (
    <>
      <SectionHeader
        eyebrow={demo ? "Forecast · mock model" : "Forecast · team model"}
        title="What the next week may bring."
        description="Projected accumulation from the last observed day, day by day."
        testId="forecast-header"
        actions={<SegmentedControl label="Forecast horizon" layoutId="fc-horizon" testIdPrefix="forecast-horizon" value={effHorizon} onChange={setHorizon} options={options} />}
      />
      {q.isLoading && !q.vm && <ChartSkeleton testId="forecast-loading" />}
      {q.isError && <ErrorState testId="forecast-error" title="Couldn't load forecast" message={q.error?.message} onAction={q.refetch} />}
      {q.vm && !q.isError && (
        <div className={`transition-opacity duration-300 ${q.isFetching ? "opacity-60" : ""}`}>
          <div className="grid gap-4 md:grid-cols-3" data-testid="forecast-summaries">
            {METRIC_OPTIONS.map((o) => (
              <SummaryTile key={o.value} metricKey={o.value} f={q.vm[o.value]} active={metric === o.value} onClick={() => setMetric(o.value)} horizon={effHorizon} units={units(o.value)} />
            ))}
          </div>
          <div className="mt-5 card-surface p-5 sm:p-8" data-testid="forecast-chart-card">
            <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
              <SegmentedControl label="Forecast metric" layoutId="fc-metric" testIdPrefix="forecast-metric" value={metric} onChange={setMetric} options={METRIC_OPTIONS} />
              <div className="flex flex-wrap gap-x-5 gap-y-2" data-testid="forecast-legend">
                <LegendItem color={FC.observed} label="Observed" />
                <LegendItem color={FC.forecast} label="Forecast" dashed />
                {demo && <LegendItem color={FC.band} label="Illustrative range" band />}
              </div>
            </div>
            <div data-testid="forecast-chart">
              <ForecastChart f={demo ? { ...q.vm[metric], issueLabel: demoQ.data.issueLabel } : q.vm[metric]} metric={metric} units={units(metric)} demo={demo} />
            </div>
            {!demo && <DailyStrip days={q.vm[metric].days} metric={metric} units={units(metric)} />}
            <Notes demo={demo} />
          </div>
        </div>
      )}
    </>
  );
};
