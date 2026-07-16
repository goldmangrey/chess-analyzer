import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Color, GameResult, MoveClassification
from app.repositories.games_repository import create_game, get_game_by_id
from app.repositories.move_analysis_repository import (
    bulk_replace_move_analysis,
    create_move_analysis,
    delete_analysis_for_game,
    get_classification_counts,
    get_personal_aggregates,
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
