import { History } from "lucide-react";

import { AppShell, PageHeading } from "@/components/layout";
import { EmptyState } from "@/components/ui";

export default function GamesPage() {
  return (
    <AppShell activeSection="games">
      <PageHeading
        eyebrow="Games"
        title="Партии"
        description="Здесь появится история импортированных партий и переход к подробному анализу."
      />
      <div className="mt-10">
        <EmptyState
          icon={<History aria-hidden="true" size={22} />}
          title="История партий будет реализована на следующем этапе"
          description="Пока это безопасный placeholder без API-запросов и демонстрационных данных."
        />
      </div>
    </AppShell>
  );
}
