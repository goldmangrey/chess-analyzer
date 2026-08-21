from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite

from app.models import MoveClassification
from app.models import Color
from app.services.human_chess_metrics import aggregate_move_accuracy, build_move_human_metrics


@dataclass(frozen=True)
class PlayerMetricSnapshot:
    games: int
    user_moves: int
    games_with_move_analysis: int
    moves_with_cp_loss: int
    moves_with_classification: int
    average_cp_loss: float | None
    inaccuracies: int
    mistakes: int
    blunders: int
    inaccuracies_per_game: float | None
    mistakes_per_game: float | None
    blunders_per_game: float | None
    inaccuracies_per_100_moves: float | None
    mistakes_per_100_moves: float | None
    blunders_per_100_moves: float | None
    serious_errors_per_100_moves: float | None
    blunder_free_games: int
    blunder_free_rate: float | None
    accuracy: float | None = None
    accuracy_eligible_moves: int = 0
    accuracy_coverage_rate: float | None = None
    accuracy_quality_band: str | None = None


def _classification(value) -> MoveClassification | None:
    if isinstance(value, MoveClassification):
        return value
    try:
        return MoveClassification(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _rate(numerator: int | float, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    value = float(numerator) / denominator
    return value if isfinite(value) else None


def build_metric_snapshot(
    games: Sequence,
    moves: Sequence,
) -> PlayerMetricSnapshot:
    user_moves = tuple(move for move in moves if getattr(move, "is_user_move", False))
    by_game: dict[int, list] = defaultdict(list)
    for move in user_moves:
        by_game[move.game_id].append(move)
    classifications = tuple(
        classification
        for move in user_moves
        if (classification := _classification(getattr(move, "classification", None)))
        is not None
    )
    cp_losses: list[float] = []
    for move in user_moves:
        try:
            value = float(getattr(move, "centipawn_loss", None))
        except (TypeError, ValueError, OverflowError):
            continue
        if isfinite(value):
            cp_losses.append(value)
    counts = Counter(classifications)
    move_accuracies = []
    for move in user_moves:
        try:
            color = move.player_color if isinstance(move.player_color, Color) else Color(move.player_color)
        except (AttributeError, TypeError, ValueError):
            move_accuracies.append(None)
            continue
        metric = build_move_human_metrics(
            getattr(move, "evaluation_before_cp", None),
            getattr(move, "evaluation_after_cp", None),
            user_color=color,
        )
        move_accuracies.append(metric.accuracy if metric else None)
    accuracy = aggregate_move_accuracy(move_accuracies)
    game_count = len(games)
    inaccuracies = counts[MoveClassification.INACCURACY]
    mistakes = counts[MoveClassification.MISTAKE]
    blunders = counts[MoveClassification.BLUNDER]
    games_with_moves = {game_id for game_id, rows in by_game.items() if rows}
    blunder_free = sum(
        1
        for game_id in games_with_moves
        if all(
            _classification(getattr(move, "classification", None))
            != MoveClassification.BLUNDER
            for move in by_game[game_id]
        )
    )
    return PlayerMetricSnapshot(
        games=game_count,
        user_moves=len(user_moves),
        games_with_move_analysis=len(games_with_moves),
        moves_with_cp_loss=len(cp_losses),
        moves_with_classification=len(classifications),
        average_cp_loss=sum(cp_losses) / len(cp_losses) if cp_losses else None,
        accuracy=accuracy.accuracy,
        accuracy_eligible_moves=accuracy.eligible_moves,
        accuracy_coverage_rate=accuracy.coverage_rate,
        accuracy_quality_band=accuracy.quality_band,
        inaccuracies=inaccuracies,
        mistakes=mistakes,
        blunders=blunders,
        inaccuracies_per_game=_rate(inaccuracies, game_count),
        mistakes_per_game=_rate(mistakes, game_count),
        blunders_per_game=_rate(blunders, game_count),
        inaccuracies_per_100_moves=_rate(inaccuracies * 100, len(user_moves)),
        mistakes_per_100_moves=_rate(mistakes * 100, len(user_moves)),
        blunders_per_100_moves=_rate(blunders * 100, len(user_moves)),
        serious_errors_per_100_moves=_rate(
            (mistakes + blunders) * 100,
            len(user_moves),
        ),
        blunder_free_games=blunder_free,
        blunder_free_rate=_rate(blunder_free, len(games_with_moves)),
    )
