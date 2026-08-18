import { BentoCard, Skeleton } from "@/components/ui";

export function AnalysisSkeleton() {
  return <div aria-label="Загрузка анализа партии" aria-busy="true"><BentoCard className="p-5 sm:p-7"><Skeleton rounded="full" className="h-4 w-24" /><Skeleton rounded="lg" className="mt-4 h-12 w-2/3" /><Skeleton rounded="full" className="mt-4 h-5 w-1/2" /><Skeleton rounded="lg" className="mt-5 h-20 w-full" /></BentoCard><div className="mt-6 grid gap-6 xl:grid-cols-[7fr_5fr]"><Skeleton rounded="lg" className="aspect-square w-full" /><Skeleton rounded="lg" className="h-[28rem]" /></div><Skeleton rounded="lg" className="mt-6 h-64 w-full" /><Skeleton rounded="lg" className="mt-6 h-72 w-full" /><Skeleton rounded="lg" className="mx-auto mt-6 h-80 w-full max-w-4xl" /></div>;
}
