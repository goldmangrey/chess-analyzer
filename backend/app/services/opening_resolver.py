from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from io import StringIO
from pathlib import Path
import re
from typing import Literal
from urllib.parse import unquote, urlparse

import chess
import chess.pgn


OpeningSource = Literal["local_database", "pgn_header", "provider_metadata", "eco_only", "unknown"]
OpeningConfidence = Literal["high", "medium", "low", "none"]


@dataclass(frozen=True)
class OpeningInfo:
    eco: str | None
    name: str | None
    family: str | None
    variation: str | None
    source: OpeningSource
    confidence: OpeningConfidence


@dataclass(frozen=True)
class _OpeningDatabase:
    by_moves: dict[tuple[str, ...], tuple[str, str]]
    names_by_slug: tuple[tuple[str, str], ...]


DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "openings.tsv"
_ECO_PATTERN = re.compile(r"^[A-E][0-9]{2}$")
_SLUG_WORDS = re.compile(r"[^a-z0-9]+")


def _clean(value: str | None) -> str | None:
    normalized = value.strip() if value else ""
    return normalized if normalized and normalized != "?" else None


def _eco(value: str | None) -> str | None:
    normalized = (_clean(value) or "").upper()
    return normalized if _ECO_PATTERN.fullmatch(normalized) else None


def _name_parts(name: str | None) -> tuple[str | None, str | None]:
    if not name:
        return None, None
    family, separator, variation = name.partition(":")
    return family.strip(), variation.strip() if separator and variation.strip() else None


def _slug_words(value: str) -> str:
    return _SLUG_WORDS.sub(" ", value.casefold().replace("'", "")).strip()


def _moves_from_pgn_fragment(fragment: str) -> tuple[str, ...]:
    game = chess.pgn.read_game(StringIO(fragment))
    if game is None or game.errors:
        return ()
    return tuple(move.uci() for move in game.mainline_moves())


@lru_cache(maxsize=1)
def _database() -> _OpeningDatabase:
    by_moves: dict[tuple[str, ...], tuple[str, str]] = {}
    canonical_names: set[str] = set()
    with DATABASE_PATH.open(encoding="utf-8") as source:
        header = source.readline().rstrip("\n")
        if header != "eco\tname\tpgn":
            raise RuntimeError("Opening database has an unsupported format")
        for line in source:
            eco, name, pgn = line.rstrip("\n").split("\t", 2)
            moves = _moves_from_pgn_fragment(pgn)
            if moves:
                by_moves.setdefault(moves, (eco, name))
                canonical_names.add(name)
    names_by_slug = tuple(
        sorted(
            ((_slug_words(name), name) for name in canonical_names),
            key=lambda item: (-len(item[0]), item[1]),
        )
    )
    return _OpeningDatabase(by_moves, names_by_slug)


def _from_provider_url(url: str | None) -> str | None:
    value = _clean(url)
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or parsed.netloc.casefold() not in {
        "chess.com", "www.chess.com",
    }:
        return None
    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) < 2 or path_parts[-2].casefold() != "openings":
        return None
    slug = _slug_words(unquote(path_parts[-1]).replace("-", " "))
    for canonical_slug, canonical_name in _database().names_by_slug:
        if slug == canonical_slug or slug.startswith(f"{canonical_slug} "):
            return canonical_name
    return None


def resolve_opening(
    moves: Iterable[chess.Move | str],
    *,
    eco: str | None = None,
    opening_name: str | None = None,
    eco_url: str | None = None,
) -> OpeningInfo:
    """Resolve the deepest known opening without provider-specific runtime I/O."""
    normalized_moves = tuple(move.uci() if isinstance(move, chess.Move) else move for move in moves)
    database = _database()
    match: tuple[str, str] | None = None
    for length in range(1, len(normalized_moves) + 1):
        candidate = database.by_moves.get(normalized_moves[:length])
        if candidate is not None:
            match = candidate
    if match is not None:
        resolved_eco, resolved_name = match
        family, variation = _name_parts(resolved_name)
        return OpeningInfo(resolved_eco, resolved_name, family, variation, "local_database", "high")

    normalized_eco = _eco(eco)
    header_name = _clean(opening_name)
    if header_name:
        family, variation = _name_parts(header_name)
        return OpeningInfo(normalized_eco, header_name, family, variation, "pgn_header", "medium")

    provider_name = _from_provider_url(eco_url)
    if provider_name:
        family, variation = _name_parts(provider_name)
        return OpeningInfo(normalized_eco, provider_name, family, variation, "provider_metadata", "medium")

    return OpeningInfo(
        normalized_eco,
        None,
        None,
        None,
        "eco_only" if normalized_eco else "unknown",
        "low" if normalized_eco else "none",
    )


def known_opening_ply(moves: Iterable[chess.Move | str]) -> int | None:
    normalized_moves = tuple(move.uci() if isinstance(move, chess.Move) else move for move in moves)
    matched = [
        length
        for length in range(1, len(normalized_moves) + 1)
        if normalized_moves[:length] in _database().by_moves
    ]
    return max(matched, default=None)
