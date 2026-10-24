import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { Menu, X } from "lucide-react";
import { Logo } from "@/components/common/Logo";

const LINKS = [
  { href: "#intro", label: "Product" },
  { href: "#how", label: "How It Works" },
  { href: "#stations", label: "Stations" },
  { href: "#technology", label: "Technology" },
];

export const Navbar = () => {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  const light = !scrolled && !open;
  return (
    <header
      data-testid="landing-navbar"
      className={`fixed inset-x-0 top-0 z-[1000] transition-colors duration-500 ${light ? "bg-transparent" : "glass-light border-b border-[#183F32]/[0.08]"}`}
    >
      <div className="mx-auto max-w-[1440px] px-5 sm:px-8 h-16 flex items-center justify-between">
        <Logo light={light} testId="navbar-logo-link" />
        <nav className="hidden md:flex items-center gap-1" aria-label="Primary">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              data-testid={`nav-link-${l.href.slice(1)}`}
              className={`rounded-full px-4 py-2 text-[13px] font-medium transition-colors ${light ? "text-white/85 hover:bg-white/10" : "text-[#202522]/70 hover:bg-[#183F32]/[0.06]"}`}
            >
              {l.label}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <Link
            to="/dashboard"
            data-testid="nav-dashboard-btn"
            className={`hidden sm:inline-flex rounded-full px-5 py-2 text-[13px] font-medium transition-colors ${light ? "bg-white/15 text-white hover:bg-white/25 backdrop-blur" : "bg-[#183F32] text-white hover:bg-[#0f2c22]"}`}
          >
            Dashboard
          </Link>
          <button
            type="button"
            className={`md:hidden h-10 w-10 grid place-items-center rounded-full ${light ? "text-white" : "text-[#202522]"}`}
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            data-testid="mobile-menu-toggle"
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>
      <AnimatePresence>
        {open && (
          <motion.nav
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden overflow-hidden px-5 pb-6"
            data-testid="mobile-menu"
          >
            {LINKS.map((l) => (
              <a key={l.href} href={l.href} onClick={() => setOpen(false)} data-testid={`mobile-nav-link-${l.href.slice(1)}`} className="block py-3 text-lg font-display font-medium border-b border-[#183F32]/[0.08]">
                {l.label}
              </a>
            ))}
            <Link to="/dashboard" data-testid="mobile-nav-dashboard-btn" className="mt-5 block text-center rounded-full bg-[#183F32] text-white py-3 text-sm font-medium">
              Launch Dashboard
            </Link>
          </motion.nav>
        )}
      </AnimatePresence>
    </header>
  );
};
