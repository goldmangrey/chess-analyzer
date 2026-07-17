import pytest

from app.models import Color, MoveClassification
from app.services.move_classifier import calculate_centipawn_loss, classify_move


def test_centipawn_loss_uses_player_perspective_and_never_negative() -> None:
    assert calculate_centipawn_loss(Color.WHITE, 100, 40) == 60
    assert calculate_centipawn_loss(Color.BLACK, -100, -40) == 60
    assert calculate_centipawn_loss(Color.WHITE, 0, 50) == 0
    assert calculate_centipawn_loss(Color.BLACK, 50, 0) == 0


@pytest.mark.parametrize(
    ("loss", "classification"),
    [
        (0, MoveClassification.NORMAL),
        (49, MoveClassification.NORMAL),
        (50, MoveClassification.INACCURACY),
        (99, MoveClassification.INACCURACY),
        (100, MoveClassification.MISTAKE),
        (199, MoveClassification.MISTAKE),
        (200, MoveClassification.BLUNDER),
        (10_000, MoveClassification.BLUNDER),
    ],
)
def test_classification_boundaries(loss: int, classification: MoveClassification) -> None:
    assert classify_move(loss) is classification


def test_negative_classification_input_is_rejected() -> None:
    with pytest.raises(ValueError):
        classify_move(-1)
