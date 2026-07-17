from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any

import chess
import chess.engine


MATE_SCORE = 100_000


class StockfishError(RuntimeError):
    pass


class StockfishNotFoundError(StockfishError):
    pass


class StockfishStartError(StockfishError):
    pass


class StockfishAnalysisError(StockfishError):
    pass


@dataclass(frozen=True)
class PositionAnalysis:
    evaluation_cp: int
    best_move_uci: str | None
    best_move_san: str | None
    principal_variation: tuple[str, ...]


class StockfishService:
    def __init__(
        self,
        executable_path: str,
        move_time_ms: int,
        pv_length: int,
        *,
        engine: Any | None = None,
    ) -> None:
        self.executable_path = executable_path
        self.move_time_ms = move_time_ms
        self.pv_length = pv_length
        self._engine = engine
        self._injected_engine = engine is not None
        self._started = False

    def start(self) -> "StockfishService":
        if self._started:
            return self
        if not self._injected_engine:
            path = Path(self.executable_path).expanduser()
            if not path.exists() or not path.is_file():
                raise StockfishNotFoundError(
                    f"Stockfish binary not found: {self.executable_path}"
                )
            if not path.stat().st_mode & 0o111:
                raise StockfishStartError(
                    f"Stockfish binary is not executable: {self.executable_path}"
                )
            try:
                self._engine = chess.engine.SimpleEngine.popen_uci(str(path))
            except (OSError, chess.engine.EngineError) as error:
                raise StockfishStartError(
                    f"Unable to start Stockfish: {self.executable_path}"
                ) from error
        self._started = True
        return self

    def close(self) -> None:
        if self._engine is not None and self._started:
            try:
                self._engine.quit()
            except (OSError, chess.engine.EngineError):
                pass
        self._started = False
        self._engine = None

    def __enter__(self) -> "StockfishService":
        return self.start()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    @staticmethod
    def _terminal_evaluation(board: chess.Board) -> int | None:
        outcome = board.outcome()
        if outcome is None:
            return None
        if outcome.winner is None:
            return 0
        return MATE_SCORE if outcome.winner == chess.WHITE else -MATE_SCORE

    @staticmethod
    def _white_evaluation(score: chess.engine.PovScore) -> int:
        white_score = score.white()
        if white_score.is_mate():
            mate = white_score.mate()
            return MATE_SCORE if mate is not None and mate > 0 else -MATE_SCORE
        value = white_score.score()
        if value is None:
            raise StockfishAnalysisError("Stockfish returned no evaluation")
        return int(value)

    def analyze_position(self, board: chess.Board) -> PositionAnalysis:
        if not self._started or self._engine is None:
            raise StockfishStartError("Stockfish service has not been started")
        position = board.copy(stack=False)
        terminal_evaluation = self._terminal_evaluation(position)
        if terminal_evaluation is not None:
            return PositionAnalysis(terminal_evaluation, None, None, ())

        try:
            info = self._engine.analyse(
                position,
                chess.engine.Limit(time=self.move_time_ms / 1000),
            )
            score = info.get("score")
            if not isinstance(score, chess.engine.PovScore):
                raise StockfishAnalysisError("Stockfish returned no valid score")
            raw_pv = info.get("pv") or []
            pv_moves = list(raw_pv[: self.pv_length])
            san_board = position.copy(stack=False)
            san_pv: list[str] = []
            for move in pv_moves:
                san_pv.append(san_board.san(move))
                san_board.push(move)
            best_move = pv_moves[0] if pv_moves else None
            return PositionAnalysis(
                evaluation_cp=self._white_evaluation(score),
                best_move_uci=best_move.uci() if best_move else None,
                best_move_san=position.san(best_move) if best_move else None,
                principal_variation=tuple(san_pv),
            )
        except StockfishAnalysisError:
            raise
        except (OSError, ValueError, AssertionError, chess.engine.EngineError) as error:
            raise StockfishAnalysisError("Stockfish position analysis failed") from error
