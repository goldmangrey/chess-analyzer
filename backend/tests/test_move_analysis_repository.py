import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Color, GamePhase, GameResult, MoveClassification
from app.repositories.games_repository import create_game, get_game_by_id
from app.repositories.move_analysis_repository import (
    bulk_replace_move_analysis,
    create_move_analysis,
    delete_analysis_for_game,
    get_classification_counts,
    get_personal_aggregates,
    get_phase_aggregates,
    list_moves_for_game,
    list_user_moves_for_game,
)
from app.schemas import GameCreate, MoveAnalysisCreate


def create_test_game(session: Session, external_id: str = "moves"):
    return create_game(
        session,
        GameCreate(
            external_id=external_id,
            white_username="Yeskendir",
            black_username="Opponent",
            user_color=Color.WHITE,
            result=GameResult.WIN,
            pgn="1. e4 e5",
        ),
    )


def move_data(
    game_id: int,
    ply: int,
    *,
    user: bool = True,
    loss: int = 0,
    classification: MoveClassification = MoveClassification.NORMAL,
    phase: GamePhase | None = None,
) -> MoveAnalysisCreate:
    return MoveAnalysisCreate(
        game_id=game_id,
        ply=ply,
        move_number=(ply + 1) // 2,
        player_color=Color.WHITE if ply % 2 else Color.BLACK,
        is_user_move=user,
        fen_before="fen",
        played_move_uci="e2e4" if ply % 2 else "e7e5",
        centipawn_loss=loss,
        classification=classification,
        phase=phase,
    )


def test_create_and_ordered_lists_without_hidden_commit(db_session: Session) -> None:
    game = create_test_game(db_session)
    second = create_move_analysis(db_session, move_data(game.id, 2, user=False))
    first = create_move_analysis(db_session, move_data(game.id, 1, user=True))

    assert first.id is not None and second.id is not None
    assert list_moves_for_game(db_session, game.id) == [first, second]
    assert list_user_moves_for_game(db_session, game.id) == [first]

    db_session.rollback()
    assert list_moves_for_game(db_session, game.id) == []


def test_delete_moves_does_not_delete_game(db_session: Session) -> None:
    game = create_test_game(db_session)
    create_move_analysis(db_session, move_data(game.id, 1))
    db_session.commit()

    assert delete_analysis_for_game(db_session, game.id) == 1
    db_session.flush()
    assert list_moves_for_game(db_session, game.id) == []
    assert get_game_by_id(db_session, game.id) is game


def test_counts_and_personal_aggregates_ignore_opponent(db_session: Session) -> None:
    game = create_test_game(db_session)
    moves = [
        move_data(game.id, 1, user=True, loss=10, classification=MoveClassification.NORMAL),
        move_data(game.id, 2, user=False, loss=1000, classification=MoveClassification.BLUNDER),
        move_data(game.id, 3, user=True, loss=30, classification=MoveClassification.MISTAKE),
        move_data(game.id, 4, user=True, loss=20, classification=MoveClassification.INACCURACY),
    ]
    for move in moves:
        create_move_analysis(db_session, move)

    personal_counts = get_classification_counts(db_session, game.id)
    all_counts = get_classification_counts(db_session, game.id, user_moves_only=False)
    aggregates = get_personal_aggregates(db_session, game.id)

    assert personal_counts == {"normal": 1, "inaccuracy": 1, "mistake": 1, "blunder": 0}
    assert all_counts == {"normal": 1, "inaccuracy": 1, "mistake": 1, "blunder": 1}
    assert aggregates.move_count == 3
    assert aggregates.average_cp_loss == 20.0
    assert aggregates.total_cp_loss == 60
    assert aggregates.inaccuracies_count == 1
    assert aggregates.mistakes_count == 1
    assert aggregates.blunders_count == 0


def test_empty_personal_aggregate_contract(db_session: Session) -> None:
    game = create_test_game(db_session)
    create_move_analysis(db_session, move_data(game.id, 2, user=False, loss=500))

    aggregates = get_personal_aggregates(db_session, game.id)
    assert aggregates.move_count == 0
    assert aggregates.average_cp_loss is None
    assert aggregates.total_cp_loss == 0
    assert get_classification_counts(db_session, game.id) == {
        "normal": 0,
        "inaccuracy": 0,
        "mistake": 0,
        "blunder": 0,
    }


@pytest.mark.parametrize(
    ("user_color", "user_plies"),
    [(Color.WHITE, {1, 3, 5}), (Color.BLACK, {2, 4, 6})],
)
def test_phase_aggregates_use_only_user_moves(db_session, user_color, user_plies) -> None:
    game = create_game(
        db_session,
        GameCreate(
            external_id=f"phase-{user_color.value}",
            white_username="User" if user_color is Color.WHITE else "Opponent",
            black_username="User" if user_color is Color.BLACK else "Opponent",
            user_color=user_color,
            result=GameResult.WIN,
            pgn="1. e4 e5 2. Nf3 Nc6 3. Bb5 a6",
        ),
    )
    phases = {
        1: GamePhase.OPENING, 2: GamePhase.OPENING,
        3: GamePhase.MIDDLEGAME, 4: GamePhase.MIDDLEGAME,
        5: GamePhase.MIDDLEGAME, 6: GamePhase.MIDDLEGAME,
    }
    for ply in range(1, 7):
        is_user = ply in user_plies
        create_move_analysis(db_session, move_data(
            game.id,
            ply,
            user=is_user,
            loss=10 * ply if is_user else 1000,
            classification=MoveClassification.MISTAKE if is_user else MoveClassification.BLUNDER,
            phase=phases[ply],
        ))

    aggregates = get_phase_aggregates(db_session, game.id)

    assert [row.phase for row in aggregates] == [GamePhase.OPENING, GamePhase.MIDDLEGAME]
    assert sum(row.user_moves for row in aggregates) == 3
    assert all(row.blunders == 0 for row in aggregates)
    assert all(row.average_cp_loss is not None and row.average_cp_loss < 1000 for row in aggregates)
    assert GamePhase.ENDGAME not in {row.phase for row in aggregates}


def test_bulk_replace_validates_ownership_before_delete(db_session: Session) -> None:
    game = create_test_game(db_session)
    existing = create_move_analysis(db_session, move_data(game.id, 1))

    with pytest.raises(ValueError, match="requested game_id"):
        bulk_replace_move_analysis(db_session, game.id, [move_data(game.id + 1, 2)])

    assert list_moves_for_game(db_session, game.id) == [existing]


def test_bulk_replace_orders_rows_and_does_not_commit(db_session: Session) -> None:
    game = create_test_game(db_session)
    create_move_analysis(db_session, move_data(game.id, 1))
    db_session.commit()

    replacements = bulk_replace_move_analysis(
        db_session,
        game.id,
        [move_data(game.id, 3), move_data(game.id, 1), move_data(game.id, 2)],
    )
    assert [move.ply for move in list_moves_for_game(db_session, game.id)] == [1, 2, 3]
    assert all(move.id is not None for move in replacements)

    db_session.rollback()
    assert [move.ply for move in list_moves_for_game(db_session, game.id)] == [1]


def test_failed_bulk_replace_is_atomic_after_external_rollback(db_session: Session) -> None:
    game = create_test_game(db_session)
    create_move_analysis(db_session, move_data(game.id, 1, loss=10))
    create_move_analysis(db_session, move_data(game.id, 2, user=False, loss=20))
    db_session.commit()

    invalid_replacement = move_data(game.id, 4).model_copy(update={"centipawn_loss": -1})
    with pytest.raises(IntegrityError):
        with db_session.begin():
            bulk_replace_move_analysis(
                db_session,
                game.id,
                [move_data(game.id, 3), invalid_replacement],
            )

    restored = list_moves_for_game(db_session, game.id)
    assert [(move.ply, move.centipawn_loss) for move in restored] == [(1, 10), (2, 20)]
