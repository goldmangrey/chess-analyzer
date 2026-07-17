import type { ApiGameListItem } from "@/lib/api/types";

import { GameCard } from "./game-card";

export function GameCardList({ games }: { games: ApiGameListItem[] }) {
  return <div className="grid gap-4 sm:grid-cols-2 xl:hidden">{games.map((game) => <GameCard key={game.id} game={game} />)}</div>;
}
