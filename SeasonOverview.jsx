import { Snowflake, Sun, Thermometer, AlertTriangle } from "lucide-react";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { CardSkeleton } from "@/components/common/States";
import { METRICS } from "@/config/metrics";
import { fmtNum, longDate, shortDate } from "@/lib/format";

const ICONS = { chillHours: Snowflake, chillPortions: Thermometer, gdd: Sun };
const DETAIL_LABEL = { chillHours: "Temperature range", chillPortions: "Model", gdd: "Base temperature" };
const DETAIL_VALUE = { chillHours: "32–45°F", chillPortions: "Dynamic Model", gdd: "50°F" };

const MissingBadge = ({ n, testId }) => (
  <div data-testid={testId} className="inline-flex items-center gap-2 rounded-full bg-[#C8A96B]/12 border border-[#C8A96B]/30 px-3 py-1.5 text-[11.5px] text-[#6b5526]">
    <AlertTriangle size={13} />
    {n} day{n === 1 ? "" : "s"} this season had too few readings
  </div>
);

const opt = (v, d, prefix = "") => (v == null ? "—" : `${prefix}${fmtNum(v, d)}`);

const card = (key, s, kind, index) => {
  const m = METRICS[key];
  const d = m.decimals;
  const estimated = kind === "estimated";
  const testId = `metric-card-${key}`;
  return (
    <MetricCard
      key={key}
      index={index}
      testId={testId}
      icon={ICONS[key]}
      title={m.label}
      detail={m.detail}
      tooltip={m.tooltip}
      value={s.seasonToDate}
      decimals={d}
      unit={s.units}
      caption={`${estimated ? "Estimated " : ""}${s.season ? `${s.season} ` : ""}season-to-date · through ${longDate(s.issueDate)}`}
      delta={s.pctVsPast}
      deltaLabel={s.pctDerived ? "vs past avg (derived)" : "vs past avg"}
      badge={s.daysMissing > 0 ? <MissingBadge n={s.daysMissing} testId={`${testId}-missing`} /> : null}
      range={s.pastMin != null ? { min: s.pastMin, max: s.pastMax, avg: s.pastAvg, label: s.pastLabel } : null}
      meta={[
        { label: DETAIL_LABEL[key], value: DETAIL_VALUE[key] },
        { label: "Season start", value: s.seasonStart ? longDate(s.seasonStart) : m.seasonStart },
        { label: "Next 7 days", value: opt(s.next7, d, "+"), testId: `${testId}-next7` },
        { label: s.projectedThrough ? `Projected · ${shortDate(s.projectedThrough)}` : "Projected", value: opt(s.projected, d), testId: `${testId}-projected` },
        ...(s.pastMin == null ? [{ label: "Past avg same date", value: opt(s.pastAvg, d), testId: `${testId}-past-avg` }] : []),
      ]}
    />
  );
};

export const SeasonOverview = ({ data, isLoading }) => {
  if (isLoading || !data) {
    return (
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3" data-testid="metric-cards-loading">
        {[0, 1, 2].map((i) => <CardSkeleton key={i} className="h-[440px]" />)}
      </div>
    );
  }
  return (
    <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3" data-testid="metric-cards">
      {["chillHours", "chillPortions", "gdd"].map((k, i) => card(k, data.metrics[k], data.location.kind, i))}
    </div>
  );
};
