from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from math import isfinite

from app.models import ErrorConfidence, ErrorType, GamePhase, MoveClassification
from app.services.error_taxonomy_classifier import ErrorClassification


MIN_RECURRING_GAMES = 2
MAX_EVIDENCE_PER_TAXONOMY = 5

_ERROR_SEVERITIES = {
    MoveClassification.INACCURACY,
    MoveClassification.MISTAKE,
    MoveClassification.BLUNDER,
}
_SEVERITY_ORDER = {
    MoveClassification.BLUNDER: 3,
    MoveClassification.MISTAKE: 2,
    MoveClassification.INACCURACY: 1,
}


@dataclass(frozen=True)
class TaxonomyIncident:
    game_id: int
    played_at: datetime | None
    error: ErrorClassification


@dataclass(frozen=True)
class RecurringErrorSeverity:
    inaccuracies: int
    mistakes: int
    blunders: int


@dataclass(frozen=True)
class RecurringErrorPhases:
    opening: int
    middlegame: int
    endgame: int
    unknown: int


@dataclass(frozen=True)
class RecurringErrorEvidence:
    game_id: int
    ply: int
    classification: MoveClassification
    phase: GamePhase | None
    played_move_san: str | None
    played_move_uci: str
    centipawn_loss: int


@dataclass(frozen=True)
class RecurringError:
    taxonomy: ErrorType
    incidents: int
    games_affected: int
    games_affected_rate: float | None
    incidents_per_game: float | None
    incidents_per_100_moves: float | None
    severity: RecurringErrorSeverity
    phases: RecurringErrorPhases
    evidence: tuple[RecurringErrorEvidence, ...]


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    value = numerator / denominator
    return float(value) if isfinite(value) else None


def _timestamp(value: datetime | None) -> float:
    if value is None:
        return float("-inf")
    try:
        return value.timestamp()
    except (OverflowError, OSError, ValueError):
        return float("-inf")


def aggregate_recurring_errors(
    incidents: Sequence[TaxonomyIncident],
    *,
    eligible_games: int,
    eligible_user_moves: int,
    minimum_games: int = MIN_RECURRING_GAMES,
    evidence_limit: int = MAX_EVIDENCE_PER_TAXONOMY,
) -> tuple[RecurringError, ...]:
    grouped: dict[ErrorType, list[TaxonomyIncident]] = defaultdict(list)
    seen: set[tuple[int, int, ErrorType]] = set()
    for incident in incidents:
        error = incident.error
        taxonomy = error.primary_type
        if (
            taxonomy is None
            or error.confidence == ErrorConfidence.LOW
            or error.severity not in _ERROR_SEVERITIES
        ):
            continue
        identity = (incident.game_id, error.ply, taxonomy)
        if identity in seen:
            continue
        seen.add(identity)
        grouped[taxonomy].append(incident)

    results: list[RecurringError] = []
    for taxonomy, taxonomy_incidents in grouped.items():
        affected = {incident.game_id for incident in taxonomy_incidents}
        if len(affected) < minimum_games:
            continue
        severity = Counter(incident.error.severity for incident in taxonomy_incidents)
        phases = Counter(incident.error.phase for incident in taxonomy_incidents)
        evidence = sorted(
            taxonomy_incidents,
            key=lambda incident: (
                -_SEVERITY_ORDER[incident.error.severity],
                -_timestamp(incident.played_at),
                -incident.game_id,
                incident.error.ply,
            ),
        )[:evidence_limit]
        results.append(
            RecurringError(
                taxonomy=taxonomy,
                incidents=len(taxonomy_incidents),
                games_affected=len(affected),
                games_affected_rate=_rate(len(affected), eligible_games),
                incidents_per_game=_rate(len(taxonomy_incidents), eligible_games),
                incidents_per_100_moves=_rate(
                    len(taxonomy_incidents) * 100,
                    eligible_user_moves,
                ),
                severity=RecurringErrorSeverity(
                    inaccuracies=severity[MoveClassification.INACCURACY],
                    mistakes=severity[MoveClassification.MISTAKE],
                    blunders=severity[MoveClassification.BLUNDER],
                ),
                phases=RecurringErrorPhases(
                    opening=phases[GamePhase.OPENING],
                    middlegame=phases[GamePhase.MIDDLEGAME],
                    endgame=phases[GamePhase.ENDGAME],
                    unknown=phases[None],
                ),
                evidence=tuple(
                    RecurringErrorEvidence(
                        game_id=incident.game_id,
                        ply=incident.error.ply,
                        classification=incident.error.severity,
                        phase=incident.error.phase,
                        played_move_san=incident.error.move_san,
                        played_move_uci=incident.error.move_uci,
                        centipawn_loss=incident.error.centipawn_loss,
                    )
                    for incident in evidence
                ),
            )
        )
    return tuple(
        sorted(
            results,
            key=lambda item: (
                -item.games_affected,
                -item.incidents,
                -item.severity.blunders,
                -item.severity.mistakes,
                item.taxonomy.value,
            ),
        )
    )
