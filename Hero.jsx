import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ChevronDown } from "lucide-react";

const ease = [0.22, 1, 0.36, 1];

export const Hero = () => (
  <section className="relative h-[100svh] min-h-[640px] w-full overflow-hidden bg-[#141816]" data-testid="hero-section">
    <motion.img
      src="/images/hero.jpg"
      alt="Aerial view of orchard rows stretching toward the horizon"
      className="absolute inset-0 h-full w-full object-cover"
      initial={{ scale: 1.12 }}
      animate={{ scale: 1 }}
      transition={{ duration: 2.6, ease }}
    />
    <div className="absolute inset-0 bg-gradient-to-b from-black/55 via-black/10 to-black/65" />
    <div className="relative z-10 h-full mx-auto max-w-[1440px] px-5 sm:px-8 flex flex-col items-center text-center">
      <div className="pt-[22vh]">
        <motion.p initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, delay: 0.3, ease }} className="eyebrow text-[#C8A96B]">
          Climate intelligence · California orchards
        </motion.p>
        <motion.h1
          initial={{ opacity: 0, y: 24, letterSpacing: "0.5em" }}
          animate={{ opacity: 1, y: 0, letterSpacing: "0.18em" }}
          transition={{ duration: 1.6, delay: 0.4, ease }}
          className="mt-6 text-5xl sm:text-7xl lg:text-8xl font-light text-white"
          data-testid="hero-title"
        >
          ORCHARDIQ
        </motion.h1>
        <motion.p initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1.1, delay: 0.9, ease }} className="mt-5 text-lg sm:text-2xl font-display font-medium text-white" data-testid="hero-tagline">
          Intelligence for Every Orchard.
        </motion.p>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 1.2, delay: 1.2 }} className="mt-4 max-w-xl mx-auto text-sm sm:text-base text-white/75 leading-relaxed">
          “Understand the climate shaping your orchard — from winter chill to growing-season heat.”
        </motion.p>
      </div>
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, delay: 1.4, ease }} className="mt-auto mb-24 flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
        <Link to="/dashboard" data-testid="hero-explore-dashboard-btn" className="sm:min-w-[240px] rounded-full bg-white text-[#183F32] px-8 py-3.5 text-sm font-semibold hover:bg-[#F7F7F2] transition-colors">
          Explore Dashboard
        </Link>
        <a href="#how" data-testid="hero-how-it-works-btn" className="sm:min-w-[240px] rounded-full bg-white/10 border border-white/25 text-white px-8 py-3.5 text-sm font-semibold backdrop-blur-md hover:bg-white/20 transition-colors">
          How It Works
        </a>
      </motion.div>
      <a href="#intro" aria-label="Scroll to content" data-testid="hero-scroll-indicator" className="absolute bottom-7 left-1/2 -translate-x-1/2 text-white/60 hover:text-white transition-colors">
        <motion.span className="block" animate={{ y: [0, 6, 0] }} transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}>
          <ChevronDown size={22} />
        </motion.span>
      </a>
    </div>
  </section>
);
