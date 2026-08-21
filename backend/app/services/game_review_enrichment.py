"""Request-scoped Game Report enrichment built from already loaded analysis."""

from dataclasses import dataclass
from typing import Literal, Sequence

from app.models import Color, MoveAnalysis
from app.services.error_taxonomy_classifier import ErrorClassification, MoveTaxonomyContext
from app.services.move_commentary import CommentIntentKind, generate_move_commentary
from app.services.move_explanation_facts import build_move_explanation_facts
from app.services.human_chess_metrics import MoveHumanMetrics, build_move_human_metrics
from app.services.opening_recognizer import OpeningRecognitionResult


OpeningMoveStatus = Literal["book", "deviation", "post_book", "reentry"]


@dataclass(frozen=True)
class PublicMoveCommentary:
    headline: str
    summary: str
    details: tuple[str, ...]
    recommendation: str | None
    intent: CommentIntentKind


@dataclass(frozen=True)
class MoveReviewEntry:
    ply: int
    commentary: PublicMoveCommentary
    opening_status: OpeningMoveStatus | None
    human_metrics: MoveHumanMetrics | None


def _opening_status(ply: int, opening: OpeningRecognitionResult) -> OpeningMoveStatus | None:
    if opening.source != "position_book":
        return None
    if opening.first_deviation_ply == ply:
        return "deviation"
    if opening.transposition_reentry and opening.first_reentry_ply == ply:
        return "reentry"
    if opening.last_sequence_book_ply is not None and ply <= opening.last_sequence_book_ply:
        return "book"
    if opening.first_deviation_ply is not None and ply > opening.first_deviation_ply:
        return "post_book"
    return None


def build_move_review_entries(
    *,
    moves: Sequence[MoveAnalysis],
    user_color: Color,
    errors: Sequence[ErrorClassification],
    contexts: Sequence[MoveTaxonomyContext] | None,
    opening: OpeningRecognitionResult,
) -> tuple[MoveReviewEntry, ...]:
    """Build one standard commentary per user move without queries or replay."""
    errors_by_ply = {error.ply: error for error in errors}
    contexts_by_ply = {context.row.ply: context for context in contexts or ()}
    entries: list[MoveReviewEntry] = []
    for move in moves:
        if not move.is_user_move:
            continue
        facts = build_move_explanation_facts(
            move_analysis=move,
            user_color=user_color,
            taxonomy=errors_by_ply.get(move.ply),
            taxonomy_context=contexts_by_ply.get(move.ply),
        )
        commentary = generate_move_commentary(facts, detail_level="standard")
        entries.append(
            MoveReviewEntry(
                ply=move.ply,
                commentary=PublicMoveCommentary(
                    headline=commentary.headline,
                    summary=commentary.summary,
                    details=commentary.details,
                    recommendation=commentary.recommendation,
                    intent=commentary.intent_kind,
                ),
                opening_status=_opening_status(move.ply, opening),
                human_metrics=build_move_human_metrics(
                    move.evaluation_before_cp,
                    move.evaluation_after_cp,
                    user_color=user_color,
                ),
            )
        )
    return tuple(entries)
