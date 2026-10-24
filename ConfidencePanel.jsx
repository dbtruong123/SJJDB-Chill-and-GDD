import { AlertTriangle, CheckCircle2, Radar, ShieldCheck, Info } from "lucide-react";
import { CardSkeleton } from "@/components/common/States";
import { METRICS } from "@/config/metrics";
import { fmtNum } from "@/lib/format";

const FAR_KM = 35;

const LevelBars = ({ level }) => (
  <div className="flex items-end gap-1" aria-label={`Indicative confidence level ${level} of 4`} data-testid="confidence-level-bars">
    {[1, 2, 3, 4].map((i) => (
      <span key={i} className={`w-2 rounded-sm transition-colors duration-500 ${i <= level ? "bg-[#183F32]" : "bg-[#183F32]/12"}`} style={{ height: 6 + i * 5 }} />
    ))}
  </div>
);

const tierFor = (loc) => {
  if (loc.kind === "station") return { level: 4, label: "Direct observation site" };
  if (loc.roughEstimate) return { level: 1, label: "Rough estimate" };
  if (loc.nearestKm <= 15) return { level: 3, label: "Close to a station" };
  return { level: 2, label: "Between stations" };
};

const explain = (loc) =>
  loc.kind === "station"
    ? `${loc.name} (CIMIS #${loc.id}) is a direct observation site. Values come from this station's own hourly record.`
    : `Values are kriged from the five stations. The closest, ${loc.nearestStation.name}, is ${fmtNum(loc.nearestKm, 1)} km away.`;

const Weights = ({ weights }) => (
  <div className="mt-5" data-testid="confidence-weights">
    <p className="text-[10.5px] uppercase tracking-[0.14em] text-[#202522]/45">Station contributions</p>
    <ul className="mt-2 grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-1.5 text-[12.5px]">
      {weights.map((w) => (
        <li key={w.id} className="flex justify-between gap-2">
          <span className="text-[#202522]/65">{w.name}</span>
          <span className="font-mono-num">{fmtNum(w.weight * 100, 1)}%</span>
        </li>
      ))}
    </ul>
    <p className="mt-2 text-[10.5px] text-[#202522]/40">Kriging weights can be slightly negative.</p>
  </div>
);

const ConfidenceCard = ({ location }) => {
  const t = tierFor(location);
  return (
    <div className="card-surface p-7" data-testid="confidence-panel">
      <div className="flex items-center justify-between">
        <p className="eyebrow text-[#183F32]/60">Location confidence</p>
        <LevelBars level={t.level} />
      </div>
      <div className="mt-5 flex items-center gap-3">
        {location.kind === "station" ? <ShieldCheck size={20} className="text-[#183F32]" /> : <Radar size={20} className="text-[#183F32]" />}
        <h3 className="text-lg font-semibold tracking-tight" data-testid="confidence-label">{t.label}</h3>
      </div>
      <p className="mt-3 text-sm text-[#202522]/65 leading-relaxed" data-testid="confidence-explanation">{explain(location)}</p>
      {location.roughEstimate && (
        <div role="alert" data-testid="confidence-far-warning" className="mt-5 flex gap-3 rounded-2xl bg-[#C8A96B]/12 border border-[#C8A96B]/35 p-4 text-[13px] text-[#6b5526]">
          <AlertTriangle size={16} className="shrink-0 mt-0.5" />
          <span>This site is more than {FAR_KM} km from every station, so the backend flags it as a rough estimate. Local conditions may differ substantially.</span>
        </div>
      )}
      {location.kind !== "station" && <Weights weights={location.weights} />}
      <p className="mt-5 text-[11px] text-[#202522]/40">Indicator is a distance-based guide, not a validated accuracy score.</p>
    </div>
  );
};

const DataQualityCard = ({ data, mode }) => {
  const { location, metrics } = data;
  const rows = ["chillHours", "chillPortions", "gdd"].map((k) => ({ k, n: metrics[k].daysMissing }));
  return (
    <div className="card-surface p-7" data-testid="data-quality-panel">
      <p className="eyebrow text-[#183F32]/60">Data quality</p>
      {mode === "demo" ? (
        <p className="mt-5 text-sm text-[#202522]/60" data-testid="dq-demo">Demo mode has no data-quality information. Switch to live data to see missing-day counts.</p>
      ) : location.kind === "station" ? (
        <ul className="mt-5 space-y-3 text-sm">
          {rows.map(({ k, n }) => (
            <li key={k} className="flex items-center gap-3" data-testid={`dq-missing-${k}`}>
              {n > 0 ? <AlertTriangle size={16} className="text-[#C8A96B]" /> : <CheckCircle2 size={16} className="text-[#89A98C]" />}
              {METRICS[k].label}: {n > 0 ? `${n} day${n === 1 ? "" : "s"} with too few readings this season` : "no incomplete days this season"}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-5 flex gap-3 text-sm text-[#202522]/60" data-testid="dq-estimated">
          <Info size={16} className="shrink-0 mt-0.5 text-[#202522]/40" />
          Missing-day counts are reported per station. The backend does not return them for estimated sites.
        </p>
      )}
      <p className="mt-5 text-[11px] text-[#202522]/40">Days missing = days with too few hourly readings, as reported by the backend.</p>
    </div>
  );
};

export const ConfidencePanel = ({ data, isLoading, mode }) => {
  if (isLoading || !data) {
    return (
      <div className="grid gap-5 lg:grid-cols-2">
        <CardSkeleton className="h-[240px]" />
        <CardSkeleton className="h-[240px]" />
      </div>
    );
  }
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <ConfidenceCard location={data.location} />
      <DataQualityCard data={data} mode={mode} />
    </div>
  );
};
