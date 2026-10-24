import { useEffect, useRef, useState } from "react";
import { animate, useReducedMotion } from "framer-motion";
import { fmtNum } from "@/lib/format";

export const AnimatedNumber = ({ value, decimals = 0, testId, className }) => {
  const [display, setDisplay] = useState(value);
  const prev = useRef(value);
  const reduce = useReducedMotion();
  useEffect(() => {
    const controls = animate(prev.current, value, {
      duration: reduce ? 0 : 0.9,
      ease: [0.22, 1, 0.36, 1],
      onUpdate: (v) => setDisplay(v),
    });
    prev.current = value;
    return () => controls.stop();
  }, [value, reduce]);
  return (
    <span data-testid={testId} className={className}>
      {fmtNum(display, decimals)}
    </span>
  );
};
