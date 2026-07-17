from app.models import Color, MoveClassification


def calculate_centipawn_loss(
    player_color: Color,
    best_evaluation_cp: int,
    played_evaluation_cp: int,
) -> int:
    loss = (
        best_evaluation_cp - played_evaluation_cp
        if player_color is Color.WHITE
        else played_evaluation_cp - best_evaluation_cp
    )
    return max(0, loss)


def classify_move(cp_loss: int) -> MoveClassification:
    if cp_loss < 0:
        raise ValueError("centipawn loss must not be negative")
    if cp_loss < 50:
        return MoveClassification.NORMAL
    if cp_loss < 100:
        return MoveClassification.INACCURACY
    if cp_loss < 200:
        return MoveClassification.MISTAKE
    return MoveClassification.BLUNDER
