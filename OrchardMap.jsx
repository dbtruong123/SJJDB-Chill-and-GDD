import { useEffect, useMemo, useRef } from "react";
import { MapContainer, TileLayer, Marker, Tooltip, ImageOverlay, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import { useReducedMotion } from "framer-motion";
import { Globe2, LocateFixed } from "lucide-react";
import { STATIC_STATION_VMS, CENTRAL_VALLEY_VIEW, WORLD_VIEW } from "@/data/stations";
import { fmtNum } from "@/lib/format";

const STOPS = ["#183F32", "#3f6e57", "#89A98C", "#C8A96B", "#d9804f"];
const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
export const rampColor = (t) => {
  const x = Math.min(1, Math.max(0, t)) * (STOPS.length - 1);
  const i = Math.min(STOPS.length - 2, Math.floor(x));
  const [a, b] = [hex(STOPS[i]), hex(STOPS[i + 1])];
  const f = x - i;
  return `rgb(${a.map((v, k) => Math.round(v + (b[k] - v) * f)).join(",")})`;
};
export const RAMP_CSS = `linear-gradient(90deg, ${STOPS.join(", ")})`;
export const FAR_KM = 35;

const stationIcon = (active) =>
  L.divIcon({
    className: "",
    html: `<div class="oiq-station ${active ? "is-active" : ""}"><span></span></div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });

const pinIcon = L.divIcon({ className: "", html: '<div class="oiq-pin"></div>', iconSize: [26, 26], iconAnchor: [13, 30] });

const IntroFlight = ({ enabled }) => {
  const map = useMap();
  const reduce = useReducedMotion();
  useEffect(() => {
    if (!enabled || reduce) {
      map.setView(CENTRAL_VALLEY_VIEW.center, CENTRAL_VALLEY_VIEW.zoom);
      return undefined;
    }
    const t = setTimeout(() => map.flyTo(CENTRAL_VALLEY_VIEW.center, CENTRAL_VALLEY_VIEW.zoom, { duration: 3.2 }), 500);
    return () => clearTimeout(t);
  }, [map, enabled, reduce]);
  return null;
};

const FollowPosition = ({ position }) => {
  const map = useMap();
  const first = useRef(true);
  const reduce = useReducedMotion();
  const [lat, lng] = position || [];
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    if (lat == null) return;
    const zoom = Math.max(map.getZoom(), 8);
    if (reduce) map.setView([lat, lng], zoom);
    else map.flyTo([lat, lng], zoom, { duration: 1.1 });
  }, [lat, lng, map, reduce]);
  return null;
};

const ClickToDrop = ({ onDrop }) => {
  useMapEvents({
    click(e) {
      onDrop?.(e.latlng);
    },
  });
  return null;
};

const MapControls = () => {
  const map = useMap();
  const ref = useRef(null);
  useEffect(() => {
    if (ref.current) {
      L.DomEvent.disableClickPropagation(ref.current);
    }
  }, []);
  const btn =
    "glass-dark h-9 px-3 rounded-full text-[12px] text-white/85 border border-white/10 inline-flex items-center gap-1.5 hover:text-white hover:border-white/25 transition-colors";
  return (
    <div ref={ref} className="absolute right-3 top-3 z-[500] flex gap-2">
      <button type="button" data-testid="map-world-view-btn" className={btn} onClick={() => map.flyTo(WORLD_VIEW.center, WORLD_VIEW.zoom, { duration: 1.6 })}>
        <Globe2 size={14} /> World
      </button>
      <button type="button" data-testid="map-reset-view-btn" className={btn} onClick={() => map.flyTo(CENTRAL_VALLEY_VIEW.center, CENTRAL_VALLEY_VIEW.zoom, { duration: 1.6 })}>
        <LocateFixed size={14} /> Central Valley
      </button>
    </div>
  );
};

const STEP = 0.05;
const SCALE = 12;

// Paints one pixel per grid cell, then upscales with smoothing + blur into a soft heatmap image.
const buildHeatmap = (grid) => {
  const lats = grid.points.map((p) => p.lat);
  const lons = grid.points.map((p) => p.lon);
  const [minLat, maxLat, minLon, maxLon] = [Math.min(...lats), Math.max(...lats), Math.min(...lons), Math.max(...lons)];
  const cols = Math.round((maxLon - minLon) / STEP) + 1;
  const rows = Math.round((maxLat - minLat) / STEP) + 1;
  const small = document.createElement("canvas");
  small.width = cols + 2;
  small.height = rows + 2;
  const ctx = small.getContext("2d");
  grid.points.forEach((p) => {
    const x = Math.round((p.lon - minLon) / STEP) + 1;
    const y = Math.round((maxLat - p.lat) / STEP) + 1;
    ctx.globalAlpha = p.nearest_km > FAR_KM ? 0.3 : 0.85;
    ctx.fillStyle = rampColor((p.value - grid.min) / (grid.max - grid.min || 1));
    ctx.fillRect(x, y, 1, 1);
  });
  const big = document.createElement("canvas");
  big.width = small.width * SCALE;
  big.height = small.height * SCALE;
  const bctx = big.getContext("2d");
  bctx.imageSmoothingEnabled = true;
  bctx.imageSmoothingQuality = "high";
  bctx.filter = `blur(${SCALE * 0.9}px)`;
  bctx.drawImage(small, 0, 0, big.width, big.height);
  const pad = STEP * 1.5;
  return {
    url: big.toDataURL("image/png"),
    bounds: [
      [minLat - pad, minLon - pad],
      [maxLat + pad, maxLon + pad],
    ],
  };
};

const GridLayer = ({ grid }) => {
  const img = useMemo(() => buildHeatmap(grid), [grid]);
  return <ImageOverlay url={img.url} bounds={img.bounds} opacity={0.75} interactive={false} className="oiq-heatmap" />;
};

const stationTip = (s, gridStation, units) => (
  <>
    <span className="font-medium">{s.name}</span> · CIMIS #{s.id}
    {gridStation?.value != null && (
      <span className="block text-white/70">
        {fmtNum(gridStation.value, 1)} {units} (station value)
      </span>
    )}
  </>
);

export const OrchardMap = ({ stations = STATIC_STATION_VMS, activeStationId, pin, onStationSelect, onDropPin, grid, intro = true, showControls = true, className = "", testId = "orchard-map" }) => {
  const focus = pin ? [pin.lat, pin.lng] : null;
  const activeStation = stations.find((s) => s.id === activeStationId);
  const followTarget = focus || (activeStation ? [activeStation.lat, activeStation.lng] : null);
  return (
    <div data-testid={testId} className={`relative overflow-hidden ${className}`}>
      <MapContainer center={WORLD_VIEW.center} zoom={WORLD_VIEW.zoom} minZoom={2} scrollWheelZoom={false} worldCopyJump zoomControl={false} preferCanvas className="h-full w-full" attributionControl>
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
          attribution="Tiles &copy; Esri &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors"
          maxZoom={16}
        />
        <TileLayer url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}" maxZoom={16} />
        {grid && <GridLayer grid={grid} />}
        <IntroFlight enabled={intro} />
        <FollowPosition position={followTarget} />
        {onDropPin && <ClickToDrop onDrop={onDropPin} />}
        {showControls && <MapControls />}
        {stations.map((s) => (
          <Marker
            key={s.id}
            position={[s.lat, s.lng]}
            icon={stationIcon(s.id === activeStationId && !pin)}
            title={`${s.name} station`}
            alt={`${s.name} station`}
            keyboard
            eventHandlers={{ click: () => onStationSelect?.(s.id) }}
          >
            <Tooltip direction="top" offset={[0, -10]} className="oiq-tip">
              {stationTip(s, grid?.stations.find((g) => g.station === s.id), grid?.units)}
            </Tooltip>
          </Marker>
        ))}
        {pin && (
          <Marker position={[pin.lat, pin.lng]} icon={pinIcon} title="Custom orchard pin" alt="Custom orchard pin">
            <Tooltip direction="top" offset={[0, -26]} className="oiq-tip" permanent>
              Your orchard
            </Tooltip>
          </Marker>
        )}
      </MapContainer>
    </div>
  );
};
