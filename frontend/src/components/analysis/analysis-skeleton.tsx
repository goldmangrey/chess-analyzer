import { BentoCard, Skeleton } from "@/components/ui";

export function AnalysisSkeleton() {
  return <div aria-label="Загрузка анализа партии" aria-busy="true"><BentoCard className="p-4 sm:p-5"><Skeleton rounded="full" className="h-3 w-24" /><Skeleton rounded="lg" className="mt-3 h-8 w-2/3" /><Skeleton rounded="full" className="mt-3 h-4 w-1/2" /><Skeleton rounded="lg" className="mt-4 h-14 w-full" /></BentoCard><div className="mt-4 grid gap-4 xl:grid-cols-[7fr_5fr]"><Skeleton rounded="lg" className="aspect-square w-full xl:row-span-2" /><Skeleton rounded="lg" className="h-80" /><Skeleton rounded="lg" className="h-64" /><Skeleton rounded="lg" className="h-56" /><Skeleton rounded="lg" className="h-56" /></div></div>;
}
