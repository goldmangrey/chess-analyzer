"""Factual opening aggregation for the current Player Intelligence window."""

from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

from app.models import Color, GameResult
from app.repositories.player_intelligence_repository import PlayerIntelligenceGameRow
from app.services.opening_recognizer import recognize_pgn


@dataclass(frozen=True)
class PlayerOpeningRecord:
    eco: str | None
    name: str | None
    family: str | None
    variation: str | None
    subvariation: str | None
    games: int
    wins: int
    draws: int
    losses: int


@dataclass(frozen=True)
class PlayerOpeningIntelligence:
    selected_games: int
    games_with_recognized_opening: int
    games_with_opening_identity: int
    recognition_coverage_rate: float | None
    top: tuple[PlayerOpeningRecord, ...]
    by_color: dict[Color, tuple[PlayerOpeningRecord, ...]]


@dataclass(frozen=True)
class _RecognizedGame:
    eco: str | None
    name: str | None
    family: str | None
    variation: str | None
    subvariation: str | None
    user_color: str
    result: str


def _clean(value: str | None) -> str | None:
    cleaned = value.strip() if value else ""
    return cleaned if cleaned and cleaned != "?" else None


def _record(rows: Sequence[_RecognizedGame]) -> PlayerOpeningRecord:
    first = rows[0]
    results = [row.result for row in rows]
    return PlayerOpeningRecord(
        eco=first.eco,
        name=first.name,
        family=first.family,
        variation=first.variation,
        subvariation=first.subvariation,
        games=len(rows),
        wins=sum(value == GameResult.WIN.value for value in results),
        draws=sum(value == GameResult.DRAW.value for value in results),
        losses=sum(value == GameResult.LOSS.value for value in results),
    )


def _aggregate(rows: Sequence[_RecognizedGame]) -> tuple[PlayerOpeningRecord, ...]:
    grouped: dict[tuple[str, str], list[_RecognizedGame]] = defaultdict(list)
    for row in rows:
        eco = row.eco
        name = row.name
        if eco is None and name is None:
            continue
        grouped[(eco or "", name or "")].append(row)
    records = [_record(group) for group in grouped.values()]
    records.sort(key=lambda item: (-item.games, item.name or "", item.eco or ""))
    return tuple(records)


def build_player_opening_intelligence(
    games: Sequence[PlayerIntelligenceGameRow],
) -> PlayerOpeningIntelligence:
    recognized_games = tuple(
        _RecognizedGame(
            eco=recognition.eco,
            name=recognition.name,
            family=recognition.family,
            variation=recognition.variation,
            subvariation=recognition.subvariation,
            user_color=game.user_color,
            result=game.result,
        )
        for game in games
        for recognition in (
            recognize_pgn(
                game.pgn,
                eco=_clean(game.opening_code),
                opening_name=_clean(game.opening_name),
            ),
        )
    )
    recognized = sum(game.name is not None for game in recognized_games)
    identity = sum(game.name is not None or game.eco is not None for game in recognized_games)
    return PlayerOpeningIntelligence(
        selected_games=len(games),
        games_with_recognized_opening=recognized,
        games_with_opening_identity=identity,
        recognition_coverage_rate=round(recognized / len(games), 4) if games else None,
        top=_aggregate(recognized_games),
        by_color={
            color: _aggregate(
                tuple(game for game in recognized_games if game.user_color == color.value)
            )
            for color in Color
        },
    )
