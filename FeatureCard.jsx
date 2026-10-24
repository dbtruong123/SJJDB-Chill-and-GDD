import { Reveal } from "@/components/common/Reveal";

export const FeatureCard = ({ image, title, body, index, testId }) => (
  <Reveal delay={index * 0.1} className="group" >
    <article data-testid={testId} className="h-full">
      <div className="relative aspect-[4/5] overflow-hidden rounded-[28px] bg-[#183F32]">
        <img src={image} alt="" loading="lazy" className="h-full w-full object-cover transition-transform duration-1000 ease-out group-hover:scale-105" />
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-transparent" />
        <span className="absolute top-6 left-6 font-mono-num text-xs text-white/70">0{index + 1}</span>
        <div className="absolute inset-x-0 bottom-0 p-7">
          <h3 className="text-2xl font-semibold tracking-tight text-white">{title}</h3>
          <p className="mt-2 text-sm text-white/75 leading-relaxed">{body}</p>
        </div>
      </div>
    </article>
  </Reveal>
);
