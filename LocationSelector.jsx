import { useState } from "react";
import { Check, MapPin, Radio, Crosshair } from "lucide-react";
import { regionFor } from "@/data/stations";
import { SegmentedControl } from "@/components/common/SegmentedControl";
import { Skeleton } from "@/components/ui/skeleton";
import { fmtCoord, fmtNum } from "@/lib/format";

const StationList = ({ stations, activeId, onSelect }) => (
  <ul className="mt-5 space-y-1.5" data-testid="station-list">
    {!stations && [0, 1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-[60px] rounded-2xl bg-[#183F32]/[0.05]" />)}
    {stations?.map((s) => {
      const active = s.id === activeId;
      return (
        <li key={s.id}>
          <button
            type="button"
            data-testid={`station-option-${s.id}`}
            aria-pressed={active}
            onClick={() => onSelect(s.id)}
            className={`group w-full flex items-center gap-4 rounded-2xl px-4 py-3 text-left transition-colors duration-200 border ${
              active ? "bg-[#183F32] border-[#183F32] text-white" : "border-transparent hover:bg-[#183F32]/[0.04]"
            }`}
          >
            <span className={`h-9 w-9 shrink-0 rounded-xl grid place-items-center ${active ? "bg-white/10" : "bg-[#183F32]/[0.06] text-[#183F32]"}`}>
              <Radio size={15} strokeWidth={1.8} />
            </span>
            <span className="flex-1 min-w-0">
              <span className="block text-[15px] font-semibold font-display">{s.name}</span>
              <span className={`block text-xs truncate ${active ? "text-white/65" : "text-[#202522]/50"}`}>
                {regionFor(s.id)}
                {s.elevationFt != null && ` · ${fmtNum(s.elevationFt)} ft`}
              </span>
            </span>
            <span className={`font-mono-num text-[11px] ${active ? "text-[#C8A96B]" : "text-[#202522]/40"}`}>#{s.id}</span>
            {active && <Check size={16} className="text-[#C8A96B]" />}
          </button>
        </li>
      );
    })}
  </ul>
);

const CoordinateForm = ({ onSubmit }) => {
  const [lat, setLat] = useState("");
  const [lng, setLng] = useState("");
  const [error, setError] = useState("");
  const submit = (e) => {
    e.preventDefault();
    const la = parseFloat(lat);
    const ln = parseFloat(lng);
    if (Number.isNaN(la) || Number.isNaN(ln) || la < 32 || la > 42.1 || ln < -124.5 || ln > -114) {
      setError("Enter a latitude between 32 and 42 and a longitude between −124.5 and −114 (California).");
      return;
    }
    setError("");
    onSubmit(la, ln);
  };
  const input =
    "w-full rounded-xl border border-[#183F32]/15 bg-[#F7F7F2] px-3 py-2.5 text-sm font-mono-num focus:outline-none focus:border-[#183F32] focus:ring-2 focus:ring-[#183F32]/10 transition";
  return (
    <form onSubmit={submit} className="mt-4" data-testid="coordinate-form" noValidate>
      <p className="text-xs text-[#202522]/50 mb-2">Or enter coordinates</p>
      <div className="grid grid-cols-2 gap-2">
        <input aria-label="Latitude" placeholder="Lat 37.10" value={lat} onChange={(e) => setLat(e.target.value)} className={input} data-testid="coord-lat-input" inputMode="decimal" />
        <input aria-label="Longitude" placeholder="Lng −120.60" value={lng} onChange={(e) => setLng(e.target.value)} className={input} data-testid="coord-lng-input" inputMode="decimal" />
      </div>
      {error && <p role="alert" className="mt-2 text-xs text-[#a1452f]" data-testid="coord-error">{error}</p>}
      <button type="submit" data-testid="coord-submit-btn" className="mt-3 w-full rounded-full border border-[#183F32] text-[#183F32] py-2.5 text-sm font-medium hover:bg-[#183F32] hover:text-white transition-colors">
        Place pin
      </button>
    </form>
  );
};

const CustomPanel = ({ pin, onCoords }) => (
  <div className="mt-5">
    {pin ? (
      <div className="rounded-2xl bg-[#C8A96B]/10 border border-[#C8A96B]/30 p-4 flex gap-3" data-testid="custom-pin-info">
        <MapPin size={18} className="text-[#8a6d33] mt-0.5" />
        <div className="text-sm">
          <p className="font-semibold text-[#202522]">Custom pin placed</p>
          <p className="text-[#202522]/60 text-xs mt-0.5">Click elsewhere on the map to move it.</p>
        </div>
      </div>
    ) : (
      <div className="rounded-2xl border border-dashed border-[#183F32]/20 p-6 text-center" data-testid="custom-pin-empty">
        <Crosshair size={22} className="mx-auto text-[#183F32]/50" />
        <p className="mt-3 text-sm font-medium text-[#202522]">No pin placed yet</p>
        <p className="mt-1 text-xs text-[#202522]/55">Click anywhere on the map to drop a pin on your orchard.</p>
      </div>
    )}
    <CoordinateForm onSubmit={onCoords} />
  </div>
);

const Detail = ({ label, value, testId }) => (
  <div>
    <dt className="text-[11px] uppercase tracking-[0.14em] text-[#202522]/45">{label}</dt>
    <dd className="mt-1 text-sm font-medium text-[#202522] font-mono-num" data-testid={testId}>{value}</dd>
  </div>
);

const distance = (km) => `${fmtNum(km, 1)} km · ${fmtNum(km / 1.60934, 1)} mi`;

export const LocationDetails = ({ location }) => {
  const station = location.kind === "station";
  return (
    <dl className="mt-6 pt-6 border-t border-[#183F32]/[0.08] grid grid-cols-2 gap-x-4 gap-y-4" data-testid="location-details">
      <Detail label="Selected" value={station ? `${location.name} · #${location.id}` : "Custom site"} testId="location-detail-name" />
      <Detail label="Type" value={station ? "Observation station" : "Estimated site"} testId="location-detail-type" />
      <Detail label="Latitude" value={fmtCoord(location.lat, "N", "S")} testId="location-detail-lat" />
      <Detail label="Longitude" value={fmtCoord(location.lng, "E", "W")} testId="location-detail-lng" />
      {station ? (
        <Detail label="Elevation" value={location.elevationFt != null ? `${fmtNum(location.elevationFt)} ft` : "—"} testId="location-detail-elevation" />
      ) : (
        <Detail label="Nearest station" value={`${location.nearestStation.name} · #${location.nearestStation.id}`} testId="location-detail-nearest" />
      )}
      <Detail label="Distance to station" value={station ? "On site" : distance(location.nearestKm)} testId="location-detail-distance" />
    </dl>
  );
};

export const LocationSelector = ({ mode, onModeChange, stations, selection, pin, onSelectStation, onCoords, children }) => (
  <div className="card-surface p-6 sm:p-7 h-full" data-testid="location-selector">
    <div>
      <p className="eyebrow text-[#183F32]/60">Orchard location</p>
      <h3 className="mt-2 text-xl font-semibold tracking-tight">Choose your site</h3>
    </div>
    <div className="mt-5">
      <SegmentedControl
        label="Location mode"
        layoutId="loc-mode"
        testIdPrefix="location-mode"
        value={mode}
        onChange={onModeChange}
        options={[
          { value: "station", label: "CIMIS stations" },
          { value: "custom", label: "Drop a pin" },
        ]}
      />
    </div>
    {mode === "station" ? (
      <StationList stations={stations} activeId={selection.type === "station" ? selection.stationId : null} onSelect={onSelectStation} />
    ) : (
      <CustomPanel pin={pin} onCoords={onCoords} />
    )}
    {children}
  </div>
);
