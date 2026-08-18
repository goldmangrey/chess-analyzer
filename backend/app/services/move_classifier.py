from app.models import Color, MoveClassification


MAX_CP_LOSS = 1_000


def calculate_centipawn_loss(
    player_color: Color,
    best_evaluation_cp: int,
    played_evaluation_cp: int,
) -> int:
    before_from_player_pov = best_evaluation_cp if player_color is Color.WHITE else -best_evaluation_cp
    after_from_player_pov = played_evaluation_cp if player_color is Color.WHITE else -played_evaluation_cp
    raw_cp_loss = before_from_player_pov - after_from_player_pov
    return min(max(0, raw_cp_loss), MAX_CP_LOSS)


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
