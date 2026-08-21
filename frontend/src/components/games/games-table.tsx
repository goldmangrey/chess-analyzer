import type { ApiGameListItem } from "@/lib/api/types";

import { GameRow } from "./game-row";

const headings = ["Соперник", "Дата", "Дебют", "Результат", "Ошибки", "Зевки", "Статус", "Действие"];

export function GamesTable({ games }: { games: ApiGameListItem[] }) {
  return (
    <div className="hidden xl:block">
      <table className="w-full border-separate border-spacing-y-1 text-left">
        <caption className="sr-only">История шахматных партий</caption>
        <thead><tr>{headings.map((heading) => <th key={heading} scope="col" className="px-3 pb-3 text-xs font-semibold text-text-muted first:pl-4 last:pr-4">{heading}</th>)}</tr></thead>
        <tbody>{games.map((game) => <GameRow key={game.id} game={game} />)}</tbody>
      </table>
    </div>
  );
}
