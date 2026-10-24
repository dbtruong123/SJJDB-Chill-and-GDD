import { Layers } from "lucide-react";
import { SegmentedControl } from "@/components/common/SegmentedControl";
import { RAMP_CSS, FAR_KM } from "@/components/OrchardMap";
import { METRIC_OPTIONS } from "@/config/metrics";
import { fmtNum, longDate } from "@/lib/format";

const VALUE_OPTIONS = [
  { value: "next7", label: "Next 7 days" },
  { value: "season_to_date", label: "Season to date" },
  { value: "projected", label: "Projected" },
];

export const MapLayerPanel = ({ metric, value, onMetric, onValue, grid, isLoading, isError, mode }) => (
  <div className="absolute left-3 top-3 z-[500] max-w-[calc(100%-1.5rem)] glass-dark rounded-2xl border border-white/10 p-3 text-white" data-testid="map-layer-panel">
    <p className="flex items-center gap-1.5 text-[10.5px] uppercase tracking-[0.16em] text-white/55">
      <Layers size={12} /> Interpolated layer
    </p>
    {mode === "demo" ? (
      <p className="mt-2 text-xs text-white/60 max-w-[220px]" data-testid="map-layer-demo-note">Not available in demo mode.</p>
    ) : (
      <>
        <div className="mt-2 flex flex-col gap-2">
          <SegmentedControl dark label="Map metric" layoutId="map-metric" testIdPrefix="map-metric" value={metric} onChange={onMetric} options={METRIC_OPTIONS} />
          <SegmentedControl dark label="Map value" layoutId="map-value" testIdPrefix="map-value" value={value} onChange={onValue} options={VALUE_OPTIONS} />
        </div>
        {isError && <p className="mt-2 text-xs text-[#f0b29a]" role="alert" data-testid="map-layer-error">Map layer unavailable.</p>}
        {grid && !isError && (
          <div className={`mt-3 transition-opacity ${isLoading ? "opacity-50" : ""}`} data-testid="map-legend">
            <div className="h-2 rounded-full" style={{ background: RAMP_CSS }} />
            <div className="mt-1 flex justify-between font-mono-num text-[10.5px] text-white/70">
              <span data-testid="map-legend-min">{fmtNum(grid.min, 1)}</span>
              <span className="text-white/45">{grid.units}</span>
              <span data-testid="map-legend-max">{fmtNum(grid.max, 1)}</span>
            </div>
            <p className="mt-2 text-[10.5px] leading-snug text-white/50 max-w-[260px]">
              Kriged estimate between stations, not measured. Faded cells are &gt;{FAR_KM} km from a station. Data through {longDate(grid.issueDate)}.
            </p>
          </div>
        )}
      </>
    )}
  </div>
);
