"""Human-readable chess metrics derived from persisted engine evaluations.

The formulas follow the public Lichess Accuracy documentation.  This module is
pure: it performs no engine, database, or network work.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from math import exp, isfinite, sqrt
from typing import Literal

from app.models import Color


HUMAN_METRICS_VERSION = "1"
MATE_EVALUATION_CP = 100_000
MIN_VOLATILITY_WEIGHT = 0.5
MAX_VOLATILITY_WEIGHT = 12.0

AccuracyQualityBand = Literal["excellent", "good", "fair", "poor"]


@dataclass(frozen=True)
class MoveHumanMetrics:
    win_percent_before: float
    win_percent_after: float
    win_percent_loss: float
    accuracy: float
    quality_band: AccuracyQualityBand


@dataclass(frozen=True)
class AccuracyAggregate:
    accuracy: float | None
    eligible_moves: int
    total_moves: int
    coverage_rate: float | None
    quality_band: AccuracyQualityBand | None


def _finite(value) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if isfinite(number) else None


def quality_band(accuracy: float | None) -> AccuracyQualityBand | None:
    """Conservative V1 presentation bands, not chess-skill/Elo grades."""
    if accuracy is None or not isfinite(accuracy):
        return None
    if accuracy >= 90:
        return "excellent"
    if accuracy >= 75:
        return "good"
    if accuracy >= 50:
        return "fair"
    return "poor"


def cp_to_win_percent(evaluation_cp) -> float | None:
    """Map a white-POV centipawn score to Win% without overflow."""
    cp = _finite(evaluation_cp)
    if cp is None:
        return None
    if cp >= MATE_EVALUATION_CP:
        return 100.0
    if cp <= -MATE_EVALUATION_CP:
        return 0.0
    exponent = -0.00368208 * cp
    if exponent >= 0:
        factor = exp(-exponent)
        value = 100.0 * factor / (1.0 + factor)
    else:
        value = 100.0 / (1.0 + exp(exponent))
    return min(max(value, 0.0), 100.0)


def move_accuracy_from_win_percent(before: float, after: float) -> float:
    loss = max(0.0, before - after)
    raw = 103.1668 * exp(-0.04354 * loss) - 3.1669
    # Current Lichess server semantics include a one-point uncertainty bonus.
    return min(max(raw + 1.0, 0.0), 100.0)


def build_move_human_metrics(
    evaluation_before_cp,
    evaluation_after_cp,
    *,
    user_color: Color,
) -> MoveHumanMetrics | None:
    before_cp = _finite(evaluation_before_cp)
    after_cp = _finite(evaluation_after_cp)
    if before_cp is None or after_cp is None:
        return None
    sign = 1.0 if user_color == Color.WHITE else -1.0
    before = cp_to_win_percent(sign * before_cp)
    after = cp_to_win_percent(sign * after_cp)
    if before is None or after is None:
        return None
    loss = max(0.0, before - after)
    accuracy = move_accuracy_from_win_percent(before, after)
    return MoveHumanMetrics(
        win_percent_before=round(before, 1),
        win_percent_after=round(after, 1),
        win_percent_loss=round(loss, 1),
        accuracy=round(accuracy, 1),
        quality_band=quality_band(accuracy) or "poor",
    )


def aggregate_move_accuracy(values: Sequence[float | None]) -> AccuracyAggregate:
    valid = [float(value) for value in values if value is not None and isfinite(float(value)) and 0 <= float(value) <= 100]
    total = len(values)
    if not valid:
        return AccuracyAggregate(None, 0, total, 0.0 if total else None, None)
    # Cross-game/phase/segment facts are pooled by move.  A harmonic mean would
    # collapse an entire long profile to zero after one 0%-accuracy move.
    rounded = round(sum(valid) / len(valid), 1)
    return AccuracyAggregate(
        accuracy=rounded,
        eligible_moves=len(valid),
        total_moves=total,
        coverage_rate=round(len(valid) / total, 4) if total else None,
        quality_band=quality_band(rounded),
    )


def _stddev(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def build_game_accuracy(
    moves: Sequence,
    *,
    user_color: Color,
) -> AccuracyAggregate:
    """Lichess-style volatility-weighted + harmonic game accuracy.

    Ordered all-ply MoveAnalysis rows are required so volatility windows reflect
    the whole game. Only the requested player's plies contribute to the result.
    """
    ordered = sorted(moves, key=lambda move: getattr(move, "ply", 0))
    user_rows = [move for move in ordered if getattr(move, "is_user_move", False)]
    total = len(user_rows)
    if not ordered or not user_rows:
        return AccuracyAggregate(None, 0, total, None if not total else 0.0, None)

    sign = 1.0 if user_color == Color.WHITE else -1.0
    positions: list[float | None] = [
        cp_to_win_percent(sign * float(ordered[0].evaluation_before_cp))
        if _finite(getattr(ordered[0], "evaluation_before_cp", None)) is not None
        else None
    ]
    positions.extend(
        cp_to_win_percent(sign * float(move.evaluation_after_cp))
        if _finite(getattr(move, "evaluation_after_cp", None)) is not None
        else None
        for move in ordered
    )
    window_size = min(max(len(ordered) // 10, 2), 8)
    windows: list[list[float | None]] = []
    for _ in range(max(min(window_size, len(positions)) - 2, 0)):
        windows.append(positions[:window_size])
    windows.extend(positions[index : index + window_size] for index in range(max(len(positions) - window_size + 1, 0)))
    weights = [
        min(max(_stddev([value for value in window if value is not None]), MIN_VOLATILITY_WEIGHT), MAX_VOLATILITY_WEIGHT)
        for window in windows
    ]

    accuracies: list[float] = []
    selected_weights: list[float] = []
    for index, move in enumerate(ordered):
        if not getattr(move, "is_user_move", False):
            continue
        before = positions[index]
        after = positions[index + 1]
        if before is None or after is None:
            continue
        accuracies.append(move_accuracy_from_win_percent(before, after))
        selected_weights.append(weights[index] if index < len(weights) else MIN_VOLATILITY_WEIGHT)
    if not accuracies:
        return AccuracyAggregate(None, 0, total, 0.0 if total else None, None)
    weighted = sum(value * weight for value, weight in zip(accuracies, selected_weights)) / sum(selected_weights)
    harmonic = 0.0 if any(value == 0 for value in accuracies) else len(accuracies) / sum(1.0 / value for value in accuracies)
    accuracy = round((weighted + harmonic) / 2.0, 1)
    return AccuracyAggregate(
        accuracy=accuracy,
        eligible_moves=len(accuracies),
        total_moves=total,
        coverage_rate=round(len(accuracies) / total, 4) if total else None,
        quality_band=quality_band(accuracy),
    )
