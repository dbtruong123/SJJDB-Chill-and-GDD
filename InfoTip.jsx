import { Info } from "lucide-react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

export const InfoTip = ({ text, testId, label = "More information" }) => (
  <Tooltip>
    <TooltipTrigger asChild>
      <button
        type="button"
        aria-label={label}
        data-testid={testId}
        className="inline-flex h-6 w-6 items-center justify-center rounded-full text-[#202522]/40 hover:text-[#183F32] hover:bg-[#183F32]/[0.06] transition-colors"
      >
        <Info size={14} strokeWidth={1.8} />
      </button>
    </TooltipTrigger>
    <TooltipContent className="max-w-[280px] rounded-xl bg-[#202522] text-[#F7F7F2] px-3.5 py-2.5 text-xs leading-relaxed border-0">
      {text}
    </TooltipContent>
  </Tooltip>
);
