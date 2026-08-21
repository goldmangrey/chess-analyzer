from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
import re

import chess


DATASET_PATH = Path(__file__).resolve().parents[2] / "data" / "openings.jsonl"
METADATA_PATH = Path(__file__).resolve().parents[2] / "data" / "openings.metadata.json"
ECO_PATTERN = re.compile(r"^[A-E][0-9]{2}$")


@dataclass(frozen=True)
class OpeningRecord:
    eco: str
    name: str
    family: str
    variations: tuple[str, ...]
    pgn: str
    uci: tuple[str, ...]
    epd: str
    ply: int

    @property
    def variation(self) -> str | None:
        return self.variations[0] if self.variations else None

    @property
    def subvariation(self) -> str | None:
        return ", ".join(self.variations[1:]) if len(self.variations) > 1 else None


def parse_opening_name(name: str) -> tuple[str, tuple[str, ...]]:
    canonical = name.strip()
    if not canonical:
        raise ValueError("Opening name must not be empty")
    family, separator, detail = canonical.partition(":")
    family = family.strip()
    variations = (
        tuple(part.strip() for part in detail.split(",") if part.strip())
        if separator
        else ()
    )
    return family, variations


def normalize_position_key(position: chess.Board | str) -> str:
    if isinstance(position, chess.Board):
        board = position.copy(stack=False)
    else:
        fields = position.strip().split()
        if len(fields) == 4:
            fields.extend(("0", "1"))
        if len(fields) != 6:
            raise ValueError("Position must be a four-field EPD or six-field FEN")
        try:
            board = chess.Board(" ".join(fields))
        except ValueError as error:
            raise ValueError("Invalid chess position") from error
    if not board.is_valid():
        raise ValueError("Invalid chess position")
    return board.epd(en_passant="legal")


class OpeningBook:
    def __init__(self, records: Iterable[OpeningRecord]):
        records = tuple(records)
        by_epd: dict[str, list[OpeningRecord]] = defaultdict(list)
        by_eco: dict[str, list[OpeningRecord]] = defaultdict(list)
        prefixes: set[tuple[str, ...]] = set()
        for record in records:
            by_epd[record.epd].append(record)
            by_eco[record.eco].append(record)
            prefixes.update(record.uci[:ply] for ply in range(1, record.ply + 1))
        preference = lambda item: (-item.ply, item.eco, item.name, item.uci)
        self._records = records
        self._by_epd = {
            key: tuple(sorted(values, key=preference)) for key, values in by_epd.items()
        }
        self._by_eco = {
            key: tuple(sorted(values, key=lambda item: (item.name, item.ply, item.uci)))
            for key, values in by_eco.items()
        }
        self._sequence_prefixes = frozenset(prefixes)

    @property
    def record_count(self) -> int:
        return len(self._records)

    @property
    def unique_position_count(self) -> int:
        return len(self._by_epd)

    @property
    def sequence_prefix_count(self) -> int:
        return len(self._sequence_prefixes)

    def is_sequence_prefix(self, moves: Iterable[chess.Move | str]) -> bool:
        sequence = tuple(move.uci() if isinstance(move, chess.Move) else move for move in moves)
        return sequence in self._sequence_prefixes

    def lookup_epd(self, epd: str) -> tuple[OpeningRecord, ...]:
        return self._by_epd.get(normalize_position_key(epd), ())

    def lookup_position(self, position: chess.Board | str) -> tuple[OpeningRecord, ...]:
        return self._by_epd.get(normalize_position_key(position), ())

    def preferred_position(self, position: chess.Board | str) -> OpeningRecord | None:
        candidates = self.lookup_position(position)
        return candidates[0] if candidates else None

    def get_by_eco(self, eco: str) -> tuple[OpeningRecord, ...]:
        normalized = eco.strip().upper()
        return self._by_eco.get(normalized, ()) if ECO_PATTERN.fullmatch(normalized) else ()


def _record_from_json(payload: dict[str, object], *, line: int) -> OpeningRecord:
    try:
        eco = str(payload["eco"])
        name = str(payload["name"])
        pgn = str(payload["pgn"])
        uci = tuple(str(payload["uci"]).split())
        epd = normalize_position_key(str(payload["epd"]))
        ply = int(payload["ply"])
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError(f"Invalid opening dataset record at line {line}") from error
    if not ECO_PATTERN.fullmatch(eco) or not name or not pgn or not uci or ply != len(uci):
        raise RuntimeError(f"Invalid opening dataset record at line {line}")
    try:
        tuple(chess.Move.from_uci(move_uci) for move_uci in uci)
    except ValueError:
        raise RuntimeError(f"Invalid UCI notation at line {line}") from None
    family, variations = parse_opening_name(name)
    return OpeningRecord(eco, name, family, variations, pgn, uci, epd, ply)


@lru_cache(maxsize=1)
def load_opening_book() -> OpeningBook:
    try:
        artifact = DATASET_PATH.read_bytes()
        metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        if sha256(artifact).hexdigest() != metadata["runtime_sha256"]:
            raise RuntimeError("Opening dataset checksum mismatch")
        records = tuple(
            _record_from_json(json.loads(row), line=line)
            for line, row in enumerate(artifact.decode("utf-8").splitlines(), start=1)
            if row.strip()
        )
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError("Opening dataset is unavailable or corrupt") from error
    if not records:
        raise RuntimeError("Opening dataset is empty")
    return OpeningBook(records)
