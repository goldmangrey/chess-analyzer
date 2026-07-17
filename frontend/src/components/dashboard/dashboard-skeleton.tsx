import { BentoGrid, BentoGridItem } from "@/components/layout";
import { BentoCard, Skeleton } from "@/components/ui";

function SkeletonCard({ className }: { className?: string }) {
  return <BentoCard className={`h-full p-6 sm:p-8 ${className ?? ""}`}><Skeleton rounded="full" className="h-4 w-28" /><Skeleton rounded="lg" className="mt-6 h-16 w-3/4" /><Skeleton rounded="full" className="mt-5 h-4 w-full" /></BentoCard>;
}

export function DashboardSkeleton() {
  return (
    <BentoGrid aria-label="Загрузка Dashboard">
      <BentoGridItem className="md:col-span-6 xl:col-span-8"><SkeletonCard className="min-h-72" /></BentoGridItem>
      <BentoGridItem className="md:col-span-6 xl:col-span-4"><SkeletonCard className="min-h-72" /></BentoGridItem>
      <BentoGridItem className="md:col-span-3 xl:col-span-5"><SkeletonCard className="min-h-52" /></BentoGridItem>
      <BentoGridItem className="md:col-span-3 xl:col-span-7"><SkeletonCard className="min-h-52" /></BentoGridItem>
      <BentoGridItem className="md:col-span-6 xl:col-span-8"><SkeletonCard className="min-h-80" /></BentoGridItem>
      <BentoGridItem className="md:col-span-6 xl:col-span-4"><SkeletonCard className="min-h-80" /></BentoGridItem>
    </BentoGrid>
  );
}
