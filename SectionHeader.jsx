import { Reveal } from "@/components/common/Reveal";

export const SectionHeader = ({ eyebrow, title, description, actions, testId }) => (
  <Reveal className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6 mb-10">
    <div className="max-w-2xl" data-testid={testId}>
      <p className="eyebrow text-[#183F32]/70">{eyebrow}</p>
      <h2 className="mt-3 text-3xl sm:text-4xl font-semibold tracking-tight text-[#202522]">{title}</h2>
      {description && <p className="mt-3 text-sm sm:text-base text-[#202522]/60 leading-relaxed">{description}</p>}
    </div>
    {actions && <div className="flex flex-wrap items-center gap-3">{actions}</div>}
  </Reveal>
);
