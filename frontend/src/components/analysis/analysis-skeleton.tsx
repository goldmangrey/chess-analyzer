import { BentoCard, Skeleton } from "@/components/ui";

export function AnalysisSkeleton() {
  return <div aria-label="Загрузка анализа партии" aria-busy="true"><BentoCard className="p-6 sm:p-8"><Skeleton rounded="full" className="h-4 w-24" /><Skeleton rounded="lg" className="mt-5 h-14 w-2/3" /><Skeleton rounded="full" className="mt-5 h-5 w-1/2" /></BentoCard><div className="mt-6 grid gap-6 xl:grid-cols-[7fr_5fr]"><Skeleton rounded="lg" className="aspect-square w-full" /><div className="grid gap-6 md:grid-cols-2 xl:grid-cols-1"><Skeleton rounded="lg" className="h-[32rem]" /><Skeleton rounded="lg" className="h-72" /></div></div><Skeleton rounded="lg" className="mt-6 h-80 w-full" /></div>;
}
