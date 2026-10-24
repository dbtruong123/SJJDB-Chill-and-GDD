import { AlertTriangle, RotateCcw } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

export const CardSkeleton = ({ className = "h-[260px]", testId }) => (
  <div data-testid={testId} className={`card-surface p-7 ${className}`}>
    <Skeleton className="h-3 w-24 bg-[#183F32]/[0.07]" />
    <Skeleton className="mt-6 h-12 w-40 bg-[#183F32]/[0.07]" />
    <Skeleton className="mt-4 h-3 w-56 bg-[#183F32]/[0.06]" />
    <Skeleton className="mt-10 h-2 w-full bg-[#183F32]/[0.05]" />
  </div>
);

export const ChartSkeleton = ({ testId }) => (
  <div data-testid={testId} className="h-[380px] w-full rounded-2xl bg-[#183F32]/[0.03] flex items-end gap-2 p-6">
    {Array.from({ length: 24 }).map((_, i) => (
      <Skeleton key={i} className="flex-1 bg-[#183F32]/[0.06]" style={{ height: `${20 + ((i * 37) % 70)}%` }} />
    ))}
  </div>
);

export const ErrorState = ({ title = "Something went wrong", message, onAction, actionLabel = "Try again", testId }) => (
  <div data-testid={testId} role="alert" className="card-surface p-8 sm:p-10 flex flex-col sm:flex-row sm:items-center gap-6">
    <div className="h-12 w-12 shrink-0 rounded-2xl bg-[#C8A96B]/15 text-[#8a6d33] grid place-items-center">
      <AlertTriangle size={20} strokeWidth={1.8} />
    </div>
    <div className="flex-1">
      <h3 className="text-lg font-semibold text-[#202522]">{title}</h3>
      <p className="mt-1 text-sm text-[#202522]/60 leading-relaxed">{message}</p>
    </div>
    {onAction && (
      <button
        type="button"
        onClick={onAction}
        data-testid={`${testId}-action`}
        className="inline-flex items-center gap-2 rounded-full bg-[#183F32] text-white px-5 py-2.5 text-sm font-medium hover:bg-[#0f2c22] transition-colors"
      >
        <RotateCcw size={14} /> {actionLabel}
      </button>
    )}
  </div>
);
