from io import StringIO

import chess
import chess.pgn

from app.models import Color, Game
from app.schemas import MoveAnalysisCreate
from app.services.move_classifier import calculate_centipawn_loss, classify_move
from app.services.game_phase_detector import GamePhaseDetector
from app.services.opening_resolver import known_opening_ply
from app.services.stockfish_service import StockfishError, StockfishService


class GameAnalysisError(RuntimeError):
    pass


def analyze_game_moves(
    game: Game,
    stockfish: StockfishService,
) -> tuple[MoveAnalysisCreate, ...]:
    """Analyze every mainline ply; principal variation is stored as SAN text."""
    try:
        parsed_game = chess.pgn.read_game(StringIO(game.pgn))
    except (ValueError, UnicodeError) as error:
        raise GameAnalysisError(f"Unable to parse saved PGN: {error}") from error
    if parsed_game is None or parsed_game.errors:
        detail = str(parsed_game.errors[0]) if parsed_game and parsed_game.errors else "no game"
        raise GameAnalysisError(f"Unable to parse saved PGN: {detail}")
    if (
        parsed_game.headers.get("White", "?") == "?"
        or parsed_game.headers.get("Black", "?") == "?"
        or parsed_game.headers.get("Result", "*") not in {"1-0", "0-1", "1/2-1/2"}
    ):
        raise GameAnalysisError("Saved PGN is missing players or a completed result")

    board = parsed_game.board()
    mainline_moves = tuple(parsed_game.mainline_moves())
    phase_detector = GamePhaseDetector(known_opening_end_ply=known_opening_ply(mainline_moves))
    analyses: list[MoveAnalysisCreate] = []
    try:
        for ply, move in enumerate(mainline_moves, start=1):
            player_color = Color.WHITE if board.turn == chess.WHITE else Color.BLACK
            fen_before = board.fen()
            move_number = board.fullmove_number
            played_move_san = board.san(move)
            phase = phase_detector.detect(board, ply)
            before = stockfish.analyze_position(board)
            board.push(move)
            after = stockfish.analyze_position(board)
            cp_loss = calculate_centipawn_loss(
                player_color,
                before.evaluation_cp,
                after.evaluation_cp,
            )
            analyses.append(
                MoveAnalysisCreate(
                    game_id=game.id,
                    ply=ply,
                    move_number=move_number,
                    player_color=player_color,
                    is_user_move=player_color is game.user_color,
                    fen_before=fen_before,
                    played_move_uci=move.uci(),
                    played_move_san=played_move_san,
                    best_move_uci=before.best_move_uci,
                    best_move_san=before.best_move_san,
                    evaluation_before_cp=before.evaluation_cp,
                    evaluation_after_cp=after.evaluation_cp,
                    centipawn_loss=cp_loss,
                    classification=classify_move(cp_loss),
                    phase=phase,
                    principal_variation=" ".join(before.principal_variation) or None,
                )
            )
    except (ValueError, AssertionError, StockfishError) as error:
        raise GameAnalysisError(f"Unable to analyze game {game.id}: {error}") from error
    return tuple(analyses)
