import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { useReducedMotion } from "framer-motion";
import { ArrowUpRight, FlaskConical, Archive, Radio, WifiOff, Loader2 } from "lucide-react";
import { Logo } from "@/components/common/Logo";
import { useDataMode } from "@/context/DataModeContext";
import { useHealth } from "@/hooks/useOrchardData";
import { longDate } from "@/lib/format";

export const DASHBOARD_SECTIONS = [
  { id: "overview", label: "Overview" },
  { id: "historical", label: "Historical Trends" },
  { id: "forecast", label: "Forecast" },
  { id: "about", label: "About" },
];

const useActiveSection = () => {
  const [active, setActive] = useState("overview");
  useEffect(() => {
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) setActive(e.target.id);
        });
      },
      { rootMargin: "-40% 0px -55% 0px" },
    );
    DASHBOARD_SECTIONS.forEach((s) => {
      const el = document.getElementById(s.id);
      if (el) obs.observe(el);
    });
    return () => obs.disconnect();
  }, []);
  return [active, setActive];
};

const NavTabs = ({ active, onGo, prefix }) => (
  <nav aria-label="Dashboard sections" className="flex items-center gap-1 overflow-x-auto">
    {DASHBOARD_SECTIONS.map((s) => (
      <button
        key={s.id}
        type="button"
        data-testid={`${prefix}-${s.id}`}
        aria-current={active === s.id ? "true" : undefined}
        onClick={() => onGo(s.id)}
        className={`whitespace-nowrap rounded-full px-4 py-2 text-[13px] font-medium transition-colors duration-200 ${
          active === s.id ? "bg-[#183F32] text-white" : "text-[#202522]/60 hover:text-[#202522] hover:bg-[#183F32]/[0.05]"
        }`}
      >
        {s.label}
      </button>
    ))}
  </nav>
);

const TONES = {
  gold: "border-[#C8A96B]/25 bg-[#C8A96B]/[0.12] text-[#6b5526]",
  sage: "border-[#89A98C]/30 bg-[#89A98C]/[0.14] text-[#24483a]",
  green: "border-[#183F32]/20 bg-[#183F32] text-white",
  red: "border-[#a1452f]/25 bg-[#a1452f]/10 text-[#7d3322]",
  neutral: "border-[#183F32]/10 bg-[#183F32]/[0.04] text-[#202522]/70",
};

const Bar = ({ tone, icon: Icon, title, text, action, testId, spin }) => (
  <div data-testid={testId} className={`border-t ${TONES[tone]}`}>
    <div className="mx-auto max-w-[1440px] px-5 sm:px-8 py-1.5 flex flex-wrap items-center justify-center gap-x-2 gap-y-1 text-[11.5px]">
      <Icon size={13} strokeWidth={1.8} className={spin ? "animate-spin" : ""} />
      <span className="font-semibold tracking-wide">{title}</span>
      {text && <span className="hidden sm:inline opacity-80" data-testid={`${testId}-text`}>· {text}</span>}
      {action && (
        <button type="button" onClick={action.onClick} data-testid={action.testId} className="ml-1 underline underline-offset-2 font-medium hover:opacity-70">
          {action.label}
        </button>
      )}
    </div>
  </div>
);

const fmtTime = (iso) => new Date(iso).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

const SOURCE_LABEL = { archive: "CIMIS archive file", "live file": "saved live CSV", "CIMIS API": "CIMIS API" };

const bannerTitle = (h) => {
  if (h.liveUpdates && h.source === "CIMIS API") return "Connected · Live CIMIS data";
  if (h.liveUpdates) return "Connected · Live updates on, waiting for first CIMIS pull";
  if (h.source === "live file") return "Connected · Saved CIMIS readings (live updates off)";
  return "Connected · Archived CIMIS data (not live)";
};

const StatusBanner = () => {
  const { mode, setMode } = useDataMode();
  const health = useHealth();
  if (mode === "demo") {
    return (
      <Bar tone="gold" icon={FlaskConical} testId="demo-mode-banner" title="Demo Mode — Illustrative Data" text="Generated for demonstration. Not CIMIS readings or model forecasts."
        action={{ label: "Switch to live data", onClick: () => setMode("live"), testId: "switch-live-btn" }} />
    );
  }
  if (health.isLoading) return <Bar tone="neutral" icon={Loader2} spin testId="api-status-loading" title="Connecting to the OrchardIQ API…" />;
  if (health.isError) {
    return <Bar tone="red" icon={WifiOff} testId="api-status-error" title="API unavailable" text={health.error.message} action={{ label: "Retry", onClick: () => health.refetch(), testId: "api-retry-btn" }} />;
  }
  const h = health.data;
  const live = h.liveUpdates && h.source === "CIMIS API";
  const parts = [
    `Observations through ${longDate(h.issueDate)}`,
    `Source: ${SOURCE_LABEL[h.source] || h.source}`,
    `Live updates ${h.liveUpdates ? "on" : "off"}`,
    `Server refreshed ${fmtTime(h.refreshedAt)}`,
    `Checked ${fmtTime(health.dataUpdatedAt)}`,
    h.lastError && `Last refresh error: ${h.lastError}`,
  ].filter(Boolean);
  return <Bar tone={live ? "green" : "sage"} icon={live ? Radio : Archive} testId="api-status-banner" title={bannerTitle(h)} text={parts.join(" · ")} />;
};

export const DashboardNav = () => {
  const [active, setActive] = useActiveSection();
  const reduce = useReducedMotion();
  const go = (id) => {
    setActive(id);
    document.getElementById(id)?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
  };
  return (
    <header className="sticky top-0 z-[1000] glass-light border-b border-[#183F32]/[0.08]" data-testid="dashboard-nav">
      <div className="mx-auto max-w-[1440px] px-5 sm:px-8 h-16 flex items-center justify-between gap-6">
        <Logo testId="dashboard-logo-link" />
        <div className="hidden md:block">
          <NavTabs active={active} onGo={go} prefix="dash-nav" />
        </div>
        <Link to="/" data-testid="dashboard-home-link" className="inline-flex items-center gap-1 text-[13px] font-medium text-[#202522]/60 hover:text-[#183F32] transition-colors">
          Home <ArrowUpRight size={14} />
        </Link>
      </div>
      <div className="md:hidden px-4 pb-2">
        <NavTabs active={active} onGo={go} prefix="dash-nav-mobile" />
      </div>
      <StatusBanner />
    </header>
  );
};
