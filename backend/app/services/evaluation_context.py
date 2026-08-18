from enum import Enum

from app.models import Color


MATE_EVALUATION_THRESHOLD = 90_000


class MateTransition(str, Enum):
    MISSED_MATE = "missed_mate"
    ALLOWED_MATE = "allowed_mate"
    DELIVERED_MATE = "delivered_mate"
    ESCAPED_MATE = "escaped_mate"


def evaluation_to_user_pov(evaluation: int | None, user_color: Color) -> int | None:
    if evaluation is None:
        return None
    return evaluation if user_color is Color.WHITE else -evaluation


def is_winning_mate(evaluation: int) -> bool:
    return evaluation >= MATE_EVALUATION_THRESHOLD


def is_losing_mate(evaluation: int) -> bool:
    return evaluation <= -MATE_EVALUATION_THRESHOLD


def mate_transition(before: int, after: int) -> MateTransition | None:
    if is_winning_mate(before) and not is_winning_mate(after):
        return MateTransition.MISSED_MATE
    if not is_losing_mate(before) and is_losing_mate(after):
        return MateTransition.ALLOWED_MATE
    if not is_winning_mate(before) and is_winning_mate(after):
        return MateTransition.DELIVERED_MATE
    if is_losing_mate(before) and not is_losing_mate(after):
        return MateTransition.ESCAPED_MATE
    return None
