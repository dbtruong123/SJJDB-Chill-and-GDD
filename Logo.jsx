import { Link } from "react-router-dom";

export const Logo = ({ light = false, testId = "logo-link" }) => (
  <Link
    to="/"
    data-testid={testId}
    className={`group inline-flex items-center gap-2.5 font-display font-semibold tracking-[0.22em] text-[13px] ${
      light ? "text-white" : "text-[#183F32]"
    }`}
  >
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true" className="transition-transform duration-500 group-hover:rotate-90">
      <circle cx="12" cy="12" r="10.5" stroke="currentColor" strokeWidth="1.3" />
      <path d="M12 5v14M6 9h12M6 15h12" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      <circle cx="12" cy="12" r="2" fill="#C8A96B" />
    </svg>
    ORCHARDIQ
  </Link>
);
