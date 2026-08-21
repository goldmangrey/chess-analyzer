from dataclasses import replace
from io import StringIO
import json
from pathlib import Path

import chess
import chess.pgn
import pytest

from app.services.opening_book import (
    DATASET_PATH,
    OpeningBook,
    load_opening_book,
    normalize_position_key,
    parse_opening_name,
)
from scripts.update_opening_database import normalize_source


def _board(fragment: str) -> chess.Board:
    game = chess.pgn.read_game(StringIO(fragment))
    assert game is not None and not game.errors
    return game.end().board()


def test_production_dataset_exists_loads_and_has_sensible_scale():
    assert DATASET_PATH.is_file()
    book = load_opening_book()
    assert book.record_count >= 1000
    assert book.unique_position_count >= 1000


@pytest.mark.parametrize(
    ("line", "eco", "name"),
    [
        ("1. e4 e5", "C20", "King's Pawn Game"),
        ("1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5", "C50", "Italian Game: Giuoco Piano"),
        ("1. e4 e5 2. Nf3 Nc6 3. Bb5", "C60", "Ruy Lopez"),
        ("1. e4 c5", "B20", "Sicilian Defense"),
        ("1. e4 e6", "C00", "French Defense"),
        ("1. e4 c6", "B10", "Caro-Kann Defense"),
        ("1. d4 d5 2. c4", "D06", "Queen's Gambit"),
        ("1. d4 Nf6 2. c4 e6 3. Nf3 b6", "E12", "Queen's Indian Defense"),
        ("1. c4", "A10", "English Opening"),
    ],
)
def test_known_positions_resolve_to_pinned_canonical_records(line, eco, name):
    record = load_opening_book().preferred_position(_board(line))
    assert record is not None
    assert (record.eco, record.name) == (eco, name)


@pytest.mark.parametrize(
    ("name", "family", "variations"),
    [
        ("English Opening", "English Opening", ()),
        ("Ruy Lopez: Berlin Defense", "Ruy Lopez", ("Berlin Defense",)),
        (
            "Sicilian Defense: Najdorf Variation, English Attack",
            "Sicilian Defense",
            ("Najdorf Variation", "English Attack"),
        ),
        ("Family: One, Two, Three", "Family", ("One", "Two", "Three")),
    ],
)
def test_name_parsing_preserves_arbitrary_variation_levels(name, family, variations):
    assert parse_opening_name(name) == (family, variations)


def test_record_retains_full_name_depth_uci_and_normalized_epd():
    record = load_opening_book().preferred_position(_board("1. e4 c6"))
    assert record is not None
    assert record.name == "Caro-Kann Defense"
    assert record.family == "Caro-Kann Defense"
    assert record.variation is None and record.subvariation is None
    assert record.ply == len(record.uci) == 2
    assert record.epd == normalize_position_key(_board(record.pgn))


def test_fen_counters_do_not_change_position_identity():
    board = _board("1. e4 e5")
    fen = board.fen()
    epd = " ".join(fen.split()[:4])
    assert normalize_position_key(fen) == normalize_position_key(epd)


def test_transposed_legal_sequences_have_one_position_key_and_lookup():
    first = _board("1. d4 Nf6 2. c4 e6 3. Nf3 b6")
    second = _board("1. Nf3 Nf6 2. c4 e6 3. d4 b6")
    assert normalize_position_key(first) == normalize_position_key(second)
    record = load_opening_book().preferred_position(second)
    assert record is not None and record.name == "Queen's Indian Defense"


def test_unknown_position_and_eco_return_empty_results():
    assert load_opening_book().lookup_position(_board("1. a3 h6")) == ()
    assert load_opening_book().get_by_eco("Z99") == ()


def test_eco_lookup_returns_only_requested_eco_in_stable_order():
    records = load_opening_book().get_by_eco("b13")
    assert records and all(record.eco == "B13" for record in records)
    assert records == tuple(sorted(records, key=lambda item: (item.name, item.ply, item.uci)))


def test_duplicate_positions_preserve_candidates_with_deterministic_preference():
    base = load_opening_book().preferred_position(_board("1. e4 c6"))
    assert base is not None
    shallower = replace(base, name="Z Name", ply=1, uci=("e2e4",))
    same_depth = replace(base, name="A Name")
    book = OpeningBook((shallower, base, same_depth))
    assert len(book.lookup_epd(base.epd)) == 3
    assert book.preferred_position(base.epd).name == "A Name"


def test_loader_is_a_process_local_singleton():
    assert load_opening_book() is load_opening_book()


def test_generator_validates_eco_pgn_uci_epd_and_depth():
    records = normalize_source("eco\tname\tpgn\nB10\tCaro-Kann Defense\t1. e4 c6\n")
    assert records[0].uci == "e2e4 c7c6"
    assert records[0].ply == 2
    assert records[0].epd == normalize_position_key(_board(records[0].pgn))
    with pytest.raises(ValueError):
        normalize_source("eco\tname\tpgn\nZ99\tInvalid\t1. e4\n")
    with pytest.raises(ValueError):
        normalize_source("eco\tname\tpgn\nB10\tInvalid\tnot pgn\n")


def test_metadata_checksum_matches_runtime_artifact():
    metadata = json.loads((DATASET_PATH.parent / "openings.metadata.json").read_text())
    assert metadata["normalized_records"] == load_opening_book().record_count
    assert metadata["malformed_rows"] == 0


def test_runtime_module_has_no_network_dependency():
    source = Path(__import__("app.services.opening_book", fromlist=["x"]).__file__).read_text()
    assert "urllib" not in source and "requests" not in source and "http" not in source


def test_docker_and_cloud_build_context_include_runtime_artifacts():
    backend = DATASET_PATH.parents[1]
    dockerfile = (backend / "Dockerfile").read_text()
    ignore = (backend / ".gcloudignore").read_text()
    assert "openings.jsonl" in dockerfile and "openings.metadata.json" in dockerfile
    assert "!data/openings.jsonl" in ignore
