from io import StringIO
import socket

import chess
import chess.engine
import chess.pgn
import pytest

from app.models import (
    AnalysisStatus,
    Color,
    ErrorConfidence,
    ErrorType,
    Game,
    GamePhase,
    GameResult,
    MoveAnalysis,
    MoveClassification,
)
from app.services.evaluation_context import MATE_EVALUATION_THRESHOLD
from app.services.game_intelligence_service import GameIntelligenceService
import app.services.game_intelligence_service as intelligence_module


def analyzed_game(
    fen: str,
    san_moves: str,
    *,
    user_color: Color = Color.WHITE,
    status: AnalysisStatus = AnalysisStatus.COMPLETED,
    opening_name: str | None = "Test Opening",
    phases: tuple[GamePhase | None, ...] = (),
    error_ply: int | None = None,
    before: int | None = 0,
    after: int | None = -200,
    loss: int = 200,
) -> tuple[Game, list[MoveAnalysis]]:
    pgn = f'[SetUp "1"]\n[FEN "{fen}"]\n[Result "*"]\n\n{san_moves} *'
    parsed = chess.pgn.read_game(StringIO(pgn))
    assert parsed is not None and not parsed.errors
    board = parsed.board()
    rows: list[MoveAnalysis] = []
    native_user = user_color == Color.WHITE
    for ply, move in enumerate(parsed.mainline_moves(), 1):
        target = ply == error_ply
        rows.append(MoveAnalysis(
            id=ply,
            game_id=1,
            ply=ply,
            move_number=(ply + 1) // 2,
            player_color=Color.WHITE if board.turn else Color.BLACK,
            is_user_move=board.turn == native_user,
            fen_before=board.fen(),
            played_move_uci=move.uci(),
            played_move_san=board.san(move),
            evaluation_before_cp=before if target else 0,
            evaluation_after_cp=after if target else 0,
            centipawn_loss=loss if target else 0,
            classification=MoveClassification.BLUNDER if target else MoveClassification.NORMAL,
            phase=phases[ply - 1] if phases else GamePhase.OPENING,
        ))
        board.push(move)
    game = Game(
        id=1,
        external_id="intelligence",
        platform="chess.com",
        white_username="User" if user_color == Color.WHITE else "Opponent",
        black_username="User" if user_color == Color.BLACK else "Opponent",
        white_rating=1500,
        black_rating=1510,
        user_color=user_color,
        result=GameResult.LOSS,
        time_control="180+2",
        opening_code="B13",
        opening_name=opening_name,
        pgn=pgn,
        analysis_status=status,
    )
    return game, rows


def build(game: Game, moves: list[MoveAnalysis]):
    return GameIntelligenceService(object()).build(game, moves=moves)  # type: ignore[arg-type]


def test_completed_game_builds_all_unified_sections_without_endgame() -> None:
    game, moves = analyzed_game(
        chess.STARTING_FEN,
        "1. e4 e5 2. Qh5",
        phases=(GamePhase.OPENING, GamePhase.OPENING, GamePhase.MIDDLEGAME),
        error_ply=3,
        before=MATE_EVALUATION_THRESHOLD,
        after=0,
        loss=1000,
    )
    intelligence = build(game, moves)

    assert intelligence.intelligence_version == "1"
    assert intelligence.analysis.intelligence_ready is True
    assert intelligence.game.opponent == "Opponent"
    assert (intelligence.opening.eco, intelligence.opening.name) == ("B13", "Test Opening")
    assert intelligence.summary is not None
    assert (intelligence.summary.user_moves, intelligence.summary.average_cp_loss) == (2, 500.0)
    assert set(intelligence.phases) == {GamePhase.OPENING, GamePhase.MIDDLEGAME}
    assert GamePhase.ENDGAME not in intelligence.phases
    assert intelligence.critical_moments[0].type.value == "missed_mate"
    assert intelligence.errors[0].primary_type == ErrorType.MISSED_MATE
    assert intelligence.error_breakdown == {ErrorType.MISSED_MATE: 1}


def test_concrete_tactical_type_is_primary_and_breakdown_does_not_count_secondary() -> None:
    game, moves = analyzed_game(
        "6k1/8/8/4n3/8/8/1Q1R3P/6K1 w - - 0 1",
        "1. h3 Nc4",
        error_ply=1,
    )
    intelligence = build(game, moves)
    error = intelligence.errors[0]
    assert error.primary_type == ErrorType.FORK
    assert ErrorType.TACTICAL_PATTERN in error.secondary_types
    assert intelligence.error_breakdown == {ErrorType.FORK: 1}


def test_low_or_null_classification_is_retained_but_excluded_from_breakdown() -> None:
    game, moves = analyzed_game(
        "6k1/8/8/8/8/8/6P1/6K1 w - - 0 1",
        "1. g3",
        error_ply=1,
    )
    intelligence = build(game, moves)
    assert intelligence.errors[0].primary_type is None
    assert intelligence.errors[0].confidence == ErrorConfidence.LOW
    assert intelligence.error_breakdown == {}


@pytest.mark.parametrize("status", [AnalysisStatus.PENDING, AnalysisStatus.FAILED])
def test_incomplete_analysis_does_not_load_or_invent_intelligence(status) -> None:
    game, moves = analyzed_game(chess.STARTING_FEN, "1. e4", status=status)

    class NoDatabaseCalls:
        def execute(self, *args, **kwargs):
            raise AssertionError("incomplete games must not load MoveAnalysis")

    intelligence = GameIntelligenceService(NoDatabaseCalls()).build(game)  # type: ignore[arg-type]
    assert intelligence.analysis.status == status
    assert intelligence.analysis.intelligence_ready is False
    assert intelligence.summary is None
    assert intelligence.phases == {}
    assert intelligence.critical_moments == ()
    assert intelligence.errors == ()
    assert intelligence.error_breakdown == {}


def test_legacy_optional_fields_and_missing_opening_name_are_safe() -> None:
    game, moves = analyzed_game(
        chess.STARTING_FEN,
        "1. e4",
        opening_name=None,
        phases=(None,),
        error_ply=1,
        before=None,
        after=None,
    )
    moves[0].best_move_uci = None
    moves[0].best_move_san = None
    moves[0].principal_variation = None
    intelligence = build(game, moves)
    assert intelligence.opening.name is None
    assert intelligence.phases == {}
    assert intelligence.critical_moments == ()
    assert intelligence.errors[0].confidence == ErrorConfidence.LOW


def test_black_short_mate_and_quiet_game_are_safe() -> None:
    black_game, black_moves = analyzed_game(
        "6k1/6p1/8/8/8/8/8/6K1 b - - 0 1",
        "1... g6",
        user_color=Color.BLACK,
        error_ply=1,
        before=-MATE_EVALUATION_THRESHOLD,
        after=0,
        loss=1000,
    )
    black = build(black_game, black_moves)
    assert black.game.user_color == Color.BLACK
    assert black.errors[0].primary_type == ErrorType.MISSED_MATE

    quiet_game, quiet_moves = analyzed_game(chess.STARTING_FEN, "1. e4 e5")
    quiet = build(quiet_game, quiet_moves)
    assert quiet.critical_moments == () and quiet.errors == () and quiet.error_breakdown == {}


def test_build_does_not_open_stockfish_or_network(monkeypatch) -> None:
    game, moves = analyzed_game(chess.STARTING_FEN, "1. e4 e5")

    def forbidden(*args, **kwargs):
        raise AssertionError("external process/network call attempted")

    monkeypatch.setattr(chess.engine.SimpleEngine, "popen_uci", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    assert build(game, moves).analysis.intelligence_ready is True


def test_taxonomy_pgn_context_is_prepared_once_per_build(monkeypatch) -> None:
    game, moves = analyzed_game(chess.STARTING_FEN, "1. e4 e5")
    original = intelligence_module.prepare_taxonomy_contexts
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(intelligence_module, "prepare_taxonomy_contexts", counted)
    build(game, moves)
    assert calls == 1
