from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
import re

from app.models import Color, GameResult, TimeControlSegment
from app.services.player_metric_snapshot import build_metric_snapshot
from app.services.player_profile_scoring import ProfileConfidence, build_profile_confidence


ESTIMATED_MOVES_FOR_INCREMENT = 40
BULLET_MAX_ESTIMATED_SECONDS = 180
BLITZ_MAX_ESTIMATED_SECONDS = 600
_TIME_CONTROL_PATTERN = re.compile(r"^(\d+)(?:\+(\d+))?$")


@dataclass(frozen=True)
class SegmentMetrics:
    games: int
    user_moves: int
    average_cp_loss: float | None
    accuracy: float | None
    accuracy_eligible_moves: int
    accuracy_coverage_rate: float | None
    accuracy_quality_band: str | None
    mistakes_per_100_moves: float | None
    blunders_per_100_moves: float | None
    serious_errors_per_100_moves: float | None
    blunder_free_rate: float | None
    wins: int
    draws: int
    losses: int
    confidence: ProfileConfidence


@dataclass(frozen=True)
class PlayerSegments:
    time_controls: dict[TimeControlSegment, SegmentMetrics]
    colors: dict[Color, SegmentMetrics]
    games_with_known_time_control: int
    games_with_known_color: int


def classify_time_control(value: str | None) -> TimeControlSegment:
    if value is None or not (match := _TIME_CONTROL_PATTERN.fullmatch(value.strip())):
        return TimeControlSegment.UNKNOWN
    base = int(match.group(1))
    increment = int(match.group(2) or 0)
    estimated_seconds = base + ESTIMATED_MOVES_FOR_INCREMENT * increment
    if estimated_seconds < BULLET_MAX_ESTIMATED_SECONDS:
        return TimeControlSegment.BULLET
    if estimated_seconds < BLITZ_MAX_ESTIMATED_SECONDS:
        return TimeControlSegment.BLITZ
    return TimeControlSegment.RAPID


def _enum_value(value, enum_type):
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _segment_metrics(games: Sequence, moves: Sequence) -> SegmentMetrics:
    game_ids = {game.id for game in games}
    segment_moves = tuple(move for move in moves if move.game_id in game_ids)
    snapshot = build_metric_snapshot(games, segment_moves)
    results = Counter(
        result
        for game in games
        if (result := _enum_value(getattr(game, "result", None), GameResult))
        is not None
    )
    confidence = build_profile_confidence(
        sample_games=snapshot.games,
        eligible_games=snapshot.games_with_move_analysis,
        eligible_user_moves=min(
            snapshot.moves_with_cp_loss,
            snapshot.moves_with_classification,
        ),
        pattern_support_games=snapshot.games_with_move_analysis,
    )
    return SegmentMetrics(
        games=snapshot.games,
        user_moves=snapshot.user_moves,
        average_cp_loss=snapshot.average_cp_loss,
        accuracy=snapshot.accuracy,
        accuracy_eligible_moves=snapshot.accuracy_eligible_moves,
        accuracy_coverage_rate=snapshot.accuracy_coverage_rate,
        accuracy_quality_band=snapshot.accuracy_quality_band,
        mistakes_per_100_moves=snapshot.mistakes_per_100_moves,
        blunders_per_100_moves=snapshot.blunders_per_100_moves,
        serious_errors_per_100_moves=snapshot.serious_errors_per_100_moves,
        blunder_free_rate=snapshot.blunder_free_rate,
        wins=results[GameResult.WIN],
        draws=results[GameResult.DRAW],
        losses=results[GameResult.LOSS],
        confidence=confidence,
    )


def build_player_segments(games: Sequence, moves: Sequence) -> PlayerSegments:
    time_groups = {
        segment: tuple(
            game
            for game in games
            if classify_time_control(getattr(game, "time_control", None)) == segment
        )
        for segment in TimeControlSegment
    }
    color_groups = {
        color: tuple(
            game
            for game in games
            if _enum_value(getattr(game, "user_color", None), Color) == color
        )
        for color in Color
    }
    return PlayerSegments(
        time_controls={
            segment: _segment_metrics(group, moves)
            for segment, group in time_groups.items()
        },
        colors={color: _segment_metrics(group, moves) for color, group in color_groups.items()},
        games_with_known_time_control=sum(
            len(group)
            for segment, group in time_groups.items()
            if segment != TimeControlSegment.UNKNOWN
        ),
        games_with_known_color=sum(len(group) for group in color_groups.values()),
    )
