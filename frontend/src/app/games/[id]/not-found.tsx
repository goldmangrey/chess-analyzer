import Link from "next/link";

import { AppShell } from "@/components/layout";
import { EmptyState } from "@/components/ui";

export default function GameNotFound() {
  return <AppShell activeSection="games"><EmptyState title="Партия не найдена" description="Возможно, она была удалена из локальной базы." action={<Link href="/games" className="focus-ring rounded-full bg-forest px-5 py-3 text-sm font-semibold text-white">Вернуться к партиям</Link>} /></AppShell>;
}
