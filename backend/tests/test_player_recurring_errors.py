from datetime import datetime, timezone

import pytest

from app.models import ErrorConfidence, ErrorType, GamePhase, MoveClassification
from app.services.error_taxonomy_classifier import ErrorClassification
from app.services.player_recurring_errors import (
    TaxonomyIncident,
    aggregate_recurring_errors,
)


def _incident(
    game_id: int,
    ply: int,
    taxonomy: ErrorType | None,
    *,
    severity: MoveClassification = MoveClassification.MISTAKE,
    confidence: ErrorConfidence = ErrorConfidence.HIGH,
    phase: GamePhase | None = GamePhase.MIDDLEGAME,
    day: int | None = None,
    secondary: tuple[ErrorType, ...] = (),
) -> TaxonomyIncident:
    return TaxonomyIncident(
        game_id=game_id,
        played_at=(
            datetime(2026, 1, day, tzinfo=timezone.utc) if day is not None else None
        ),
        error=ErrorClassification(
            ply=ply,
            move_number=(ply + 1) // 2,
            move_san="Qh5",
            move_uci="d1h5",
            phase=phase,
            severity=severity,
            primary_type=taxonomy,
            secondary_types=secondary,
            confidence=confidence,
            centipawn_loss=200,
            critical_moment_type=None,
        ),
    )


def aggregate(*incidents, games=4, moves=100, **kwargs):
    return aggregate_recurring_errors(
        incidents,
        eligible_games=games,
        eligible_user_moves=moves,
        **kwargs,
    )


def test_empty_or_single_game_taxonomy_is_not_recurring():
    assert aggregate() == ()
    assert aggregate(_incident(1, 1, ErrorType.KING_SAFETY)) == ()
    assert aggregate(
        _incident(1, 1, ErrorType.KING_SAFETY),
        _incident(1, 3, ErrorType.KING_SAFETY),
    ) == ()


def test_recurring_metrics_use_eligible_sample_denominators():
    result = aggregate(
        _incident(1, 1, ErrorType.KING_SAFETY),
        _incident(1, 3, ErrorType.KING_SAFETY),
        _incident(2, 5, ErrorType.KING_SAFETY),
        games=5,
        moves=60,
    )[0]

    assert result.incidents == 3
    assert result.games_affected == 2
    assert result.games_affected_rate == 0.4
    assert result.incidents_per_game == 0.6
    assert result.incidents_per_100_moves == 5.0


def test_zero_eligible_denominator_returns_null_rates():
    result = aggregate_recurring_errors(
        [_incident(1, 1, ErrorType.PIN), _incident(2, 1, ErrorType.PIN)],
        eligible_games=0,
        eligible_user_moves=0,
    )[0]
    assert result.games_affected_rate is None
    assert result.incidents_per_game is None
    assert result.incidents_per_100_moves is None


def test_severity_and_phase_distributions_sum_to_incidents():
    result = aggregate(
        _incident(1, 1, ErrorType.FORK, severity=MoveClassification.INACCURACY, phase=GamePhase.OPENING),
        _incident(2, 2, ErrorType.FORK, severity=MoveClassification.MISTAKE, phase=GamePhase.MIDDLEGAME),
        _incident(3, 3, ErrorType.FORK, severity=MoveClassification.BLUNDER, phase=GamePhase.ENDGAME),
        _incident(4, 4, ErrorType.FORK, severity=MoveClassification.BLUNDER, phase=None),
    )[0]

    assert (result.severity.inaccuracies, result.severity.mistakes, result.severity.blunders) == (1, 1, 2)
    assert (result.phases.opening, result.phases.middlegame, result.phases.endgame, result.phases.unknown) == (1, 1, 1, 1)
    assert sum(vars(result.severity).values()) == result.incidents


def test_only_primary_medium_or_high_error_taxonomy_is_counted():
    incidents = [
        _incident(1, 1, ErrorType.PIN, confidence=ErrorConfidence.MEDIUM, secondary=(ErrorType.FORK,)),
        _incident(2, 1, ErrorType.PIN, confidence=ErrorConfidence.HIGH, secondary=(ErrorType.FORK,)),
        _incident(3, 1, ErrorType.PIN, confidence=ErrorConfidence.LOW),
        _incident(4, 1, ErrorType.PIN, severity=MoveClassification.NORMAL),
        _incident(5, 1, None),
    ]

    result = aggregate(*incidents)[0]

    assert result.taxonomy == ErrorType.PIN
    assert result.incidents == 2
    assert all(item.taxonomy != ErrorType.FORK for item in aggregate(*incidents))


def test_duplicate_identity_does_not_inflate_incidents():
    duplicate = _incident(1, 1, ErrorType.DEVELOPMENT)
    result = aggregate(duplicate, duplicate, _incident(2, 1, ErrorType.DEVELOPMENT))[0]
    assert result.incidents == 2


def test_evidence_is_limited_and_ranked_by_severity_freshness_and_stable_ids():
    incidents = [
        _incident(1, 1, ErrorType.HANGING_PIECE, severity=MoveClassification.INACCURACY, day=5),
        _incident(2, 2, ErrorType.HANGING_PIECE, severity=MoveClassification.BLUNDER, day=1),
        _incident(3, 3, ErrorType.HANGING_PIECE, severity=MoveClassification.MISTAKE, day=4),
        _incident(4, 4, ErrorType.HANGING_PIECE, severity=MoveClassification.BLUNDER, day=3),
        _incident(5, 5, ErrorType.HANGING_PIECE, severity=MoveClassification.MISTAKE, day=2),
        _incident(6, 6, ErrorType.HANGING_PIECE, severity=MoveClassification.BLUNDER, day=3),
    ]

    result = aggregate(*incidents, games=6, evidence_limit=5)[0]

    assert len(result.evidence) == 5
    assert [(item.game_id, item.ply) for item in result.evidence[:3]] == [(6, 6), (4, 4), (2, 2)]
    assert result.evidence[0].classification == MoveClassification.BLUNDER


def test_recurring_list_prefers_cross_game_recurrence_then_stable_taxonomy():
    incidents = [
        _incident(1, 1, ErrorType.PAWN_STRUCTURE),
        _incident(2, 1, ErrorType.PAWN_STRUCTURE),
        _incident(1, 2, ErrorType.BAD_EXCHANGE),
        _incident(2, 2, ErrorType.BAD_EXCHANGE),
        _incident(3, 2, ErrorType.BAD_EXCHANGE),
        _incident(1, 3, ErrorType.ALLOWED_MATE),
        _incident(2, 3, ErrorType.ALLOWED_MATE),
    ]

    result = aggregate(*incidents)

    assert [item.taxonomy for item in result] == [
        ErrorType.BAD_EXCHANGE,
        ErrorType.ALLOWED_MATE,
        ErrorType.PAWN_STRUCTURE,
    ]
