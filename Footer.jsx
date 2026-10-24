import { Link } from "react-router-dom";
import { Logo } from "@/components/common/Logo";

export const Footer = () => (
  <footer className="bg-[#141816] text-[#F7F7F2]" data-testid="site-footer">
    <div className="mx-auto max-w-[1440px] px-5 sm:px-8 py-16 grid gap-10 md:grid-cols-12">
      <div className="md:col-span-6">
        <Logo light testId="footer-logo-link" />
        <p className="mt-5 text-sm text-white/55 max-w-md leading-relaxed">
          Developed for Reboot the Earth 2026 — UC Davis × United Nations.
        </p>
        <p className="mt-3 text-xs text-white/40 max-w-md leading-relaxed" data-testid="footer-disclaimer">
          OrchardIQ is a hackathon prototype. It is not an official United Nations or UC Davis product. Data comes from archived CIMIS observations and the team’s forecast model; demo mode shows illustrative values only.
        </p>
      </div>
      <nav className="md:col-span-3 flex flex-col gap-3 text-sm" aria-label="Footer">
        <p className="eyebrow text-white/35">Explore</p>
        <Link to="/" data-testid="footer-home-link" className="text-white/70 hover:text-white transition-colors">Home</Link>
        <Link to="/dashboard" data-testid="footer-dashboard-link" className="text-white/70 hover:text-white transition-colors">Dashboard</Link>
        <Link to="/#how" data-testid="footer-how-link" className="text-white/70 hover:text-white transition-colors">How it works</Link>
      </nav>
      <div className="md:col-span-3 text-sm">
        <p className="eyebrow text-white/35">Measurements</p>
        <ul className="mt-3 space-y-3 text-white/70">
          <li>Chill Hours · 32–45°F</li>
          <li>Chill Portions · Dynamic Model</li>
          <li>Growing Degree Days · Base 50°F</li>
        </ul>
      </div>
    </div>
    <div className="border-t border-white/10">
      <div className="mx-auto max-w-[1440px] px-5 sm:px-8 py-6 flex flex-col sm:flex-row justify-between gap-2 text-[11px] text-white/35">
        <span>© 2026 OrchardIQ · Intelligence for Every Orchard.</span>
        <span>Map tiles © Esri, © OpenStreetMap contributors · Photos via Unsplash & Pexels</span>
      </div>
    </div>
  </footer>
);
