import "@/App.css";
import "leaflet/dist/leaflet.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { useEffect } from "react";
import { MotionConfig } from "framer-motion";
import { Toaster } from "sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { DataModeProvider } from "@/context/DataModeContext";
import LandingPage from "@/pages/LandingPage";
import Dashboard from "@/pages/Dashboard";

const ScrollToTop = () => {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
};

function App() {
  return (
    <MotionConfig reducedMotion="user">
      <DataModeProvider>
      <TooltipProvider delayDuration={150}>
        <BrowserRouter>
          <ScrollToTop />
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
        <Toaster position="bottom-center" toastOptions={{ style: { borderRadius: 14, fontFamily: "Inter" } }} />
      </TooltipProvider>
      </DataModeProvider>
    </MotionConfig>
  );
}

export default App;
