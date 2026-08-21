"""Vendor and normalize a pinned CC0 lichess-org/chess-openings snapshot.

Developer-only maintenance command. Application runtime never imports this
module and never downloads opening data.
"""

from collections import Counter
import csv
from dataclasses import asdict, dataclass
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import re
from urllib.request import urlopen

import chess
import chess.pgn


REVISION = "4b8622759e7ae6f93f011cc6c83a3823401ab45e"
SOURCE = "https://raw.githubusercontent.com/lichess-org/chess-openings/{revision}/{volume}.tsv"
DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data"
SOURCE_OUTPUT = DATA_DIRECTORY / "openings.tsv"
RUNTIME_OUTPUT = DATA_DIRECTORY / "openings.jsonl"
METADATA_OUTPUT = DATA_DIRECTORY / "openings.metadata.json"
SOURCE_FILES = tuple(f"{volume}.tsv" for volume in "abcde")
ECO_PATTERN = re.compile(r"^[A-E][0-9]{2}$")


@dataclass(frozen=True)
class GeneratedOpening:
    eco: str
    name: str
    pgn: str
    uci: str
    epd: str
    ply: int


def _parse_row(eco: str, name: str, pgn: str, *, location: str) -> GeneratedOpening:
    eco = eco.strip().upper()
    name = name.strip()
    pgn = pgn.strip()
    if not ECO_PATTERN.fullmatch(eco):
        raise ValueError(f"{location}: invalid ECO {eco!r}")
    if not name or not pgn:
        raise ValueError(f"{location}: name and PGN are required")
    game = chess.pgn.read_game(StringIO(pgn))
    if game is None or game.errors:
        raise ValueError(f"{location}: invalid PGN")
    board = game.board()
    uci: list[str] = []
    try:
        for move in game.mainline_moves():
            if move not in board.legal_moves:
                raise ValueError(f"illegal move {move.uci()}")
            uci.append(move.uci())
            board.push(move)
    except (AssertionError, ValueError) as error:
        raise ValueError(f"{location}: invalid move sequence: {error}") from error
    if not uci or not board.is_valid():
        raise ValueError(f"{location}: empty or impossible opening position")
    return GeneratedOpening(
        eco=eco,
        name=name,
        pgn=pgn,
        uci=" ".join(uci),
        epd=board.epd(en_passant="legal"),
        ply=len(uci),
    )


def normalize_source(source_text: str) -> tuple[GeneratedOpening, ...]:
    reader = csv.DictReader(StringIO(source_text), delimiter="\t")
    if reader.fieldnames != ["eco", "name", "pgn"]:
        raise ValueError("Unsupported source header")
    records = tuple(
        _parse_row(
            row.get("eco", ""),
            row.get("name", ""),
            row.get("pgn", ""),
            location=f"row {index}",
        )
        for index, row in enumerate(reader, start=2)
    )
    if not records:
        raise ValueError("Opening source is empty")
    return records


def _download_sources() -> str:
    rows: list[str] = []
    for filename in SOURCE_FILES:
        volume = filename[0]
        with urlopen(
            SOURCE.format(revision=REVISION, volume=volume), timeout=30
        ) as response:
            lines = response.read().decode("utf-8").splitlines()
        if not lines or lines[0] != "eco\tname\tpgn":
            raise RuntimeError(f"Unexpected opening database format in {filename}")
        rows.extend(lines[1:])
    return "eco\tname\tpgn\n" + "\n".join(rows) + "\n"


def _runtime_bytes(records: tuple[GeneratedOpening, ...]) -> bytes:
    return (
        "\n".join(
            json.dumps(asdict(record), ensure_ascii=False, separators=(",", ":"))
            for record in records
        )
        + "\n"
    ).encode("utf-8")


def generate(source_text: str) -> dict[str, object]:
    records = normalize_source(source_text)
    runtime = _runtime_bytes(records)
    epd_counts = Counter(record.epd for record in records)
    eco_counts = Counter(record.eco for record in records)
    metadata: dict[str, object] = {
        "source_repository": "https://github.com/lichess-org/chess-openings",
        "revision": REVISION,
        "license": "CC0-1.0",
        "source_files": list(SOURCE_FILES),
        "source_rows": len(records),
        "normalized_records": len(records),
        "unique_epd": len(epd_counts),
        "duplicate_epd_records": sum(count - 1 for count in epd_counts.values()),
        "duplicate_epd_positions": sum(count > 1 for count in epd_counts.values()),
        "unique_eco": len(eco_counts),
        "eco_volume_distribution": dict(sorted(Counter(r.eco[0] for r in records).items())),
        "runtime_artifact": RUNTIME_OUTPUT.name,
        "runtime_sha256": sha256(runtime).hexdigest(),
        "runtime_bytes": len(runtime),
        "malformed_rows": 0,
    }
    DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)
    SOURCE_OUTPUT.write_text(source_text, encoding="utf-8")
    RUNTIME_OUTPUT.write_bytes(runtime)
    METADATA_OUTPUT.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return metadata


def main() -> None:
    metadata = generate(_download_sources())
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
