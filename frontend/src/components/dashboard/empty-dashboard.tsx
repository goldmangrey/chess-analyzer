import { Cpu, Download, LineChart } from "lucide-react";

import { BentoCard } from "@/components/ui";

const steps = [
  { icon: Download, title: "Введите username", text: "Укажите профиль Chess.com в форме импорта." },
  { icon: Cpu, title: "Импортируйте партии", text: "Новые партии сохранятся в локальной SQLite базе." },
  { icon: LineChart, title: "Получите анализ", text: "Stockfish обработает каждый полуход локально." },
];

export function EmptyDashboard() {
  return (
    <BentoCard as="section" tone="lime" className="p-6 sm:p-9">
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-forest-light">Первый запуск</p>
      <h2 className="mt-3 text-3xl font-semibold tracking-[-0.05em]">Начните с реальных партий</h2>
      <div className="mt-8 grid gap-4 md:grid-cols-3">
        {steps.map((step, index) => (
          <article key={step.title} className="rounded-[1.25rem] bg-white/65 p-5">
            <div className="flex items-center justify-between"><step.icon aria-hidden="true" size={20} className="text-forest" /><span className="technical-number text-xs text-text-muted">0{index + 1}</span></div>
            <h3 className="mt-5 font-semibold">{step.title}</h3><p className="mt-2 text-sm leading-6 text-text-secondary">{step.text}</p>
          </article>
        ))}
      </div>
    </BentoCard>
  );
}
