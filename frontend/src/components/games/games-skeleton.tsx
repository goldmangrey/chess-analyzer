import { BentoCard, Skeleton } from "@/components/ui";

export function GamesSkeleton() {
  return (
    <div aria-label="Загрузка истории партий" aria-busy="true">
      <div className="flex items-end justify-between gap-5"><div className="w-full max-w-xl"><Skeleton rounded="full" className="h-4 w-24" /><Skeleton rounded="lg" className="mt-4 h-14 w-72 max-w-full" /><Skeleton rounded="full" className="mt-4 h-5 w-44" /></div><Skeleton rounded="full" className="hidden h-11 w-32 sm:block" /></div>
      <BentoCard className="mt-8 p-5"><div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">{Array.from({ length: 5 }, (_, index) => <Skeleton key={index} rounded="md" className="h-16" />)}</div></BentoCard>
      <BentoCard className="mt-6 hidden p-5 xl:block"><div className="space-y-3">{Array.from({ length: 6 }, (_, index) => <Skeleton key={index} rounded="md" className="h-16" />)}</div></BentoCard>
      <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:hidden">{Array.from({ length: 4 }, (_, index) => <Skeleton key={index} rounded="lg" className="h-72" />)}</div>
    </div>
  );
}
