from dataclasses import replace
from io import StringIO
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import chess
import chess.pgn
import pytest

from app.models import Color, ErrorConfidence, ErrorType, GamePhase, MoveClassification
from app.services.error_taxonomy_classifier import ErrorClassification
from app.services.evaluation_context import MATE_EVALUATION_THRESHOLD
from app.services.move_commentary import (
    COMMENTARY_VERSION,
    CommentIntentKind,
    CommentTemplateFamily,
    build_comment_intent,
    build_comment_plan,
    generate_move_commentary,
    russian_piece,
    stable_variant_index,
)
from app.services.move_explanation_facts import build_move_explanation_facts


def _before(fragment: str) -> tuple[str, str]:
    game = chess.pgn.read_game(StringIO(fragment))
    assert game is not None and not game.errors
    board = game.board()
    moves = tuple(game.mainline_moves())
    for move in moves[:-1]:
        board.push(move)
    return board.fen(), moves[-1].uci()


def _row(
    fen=chess.STARTING_FEN,
    played="e2e4",
    *,
    best=None,
    classification=MoveClassification.BLUNDER,
    before=0,
    after=-250,
    loss=250,
    phase=GamePhase.MIDDLEGAME,
):
    return SimpleNamespace(
        game_id=3,
        ply=7,
        fen_before=fen,
        played_move_uci=played,
        best_move_uci=best,
        classification=classification,
        phase=phase,
        evaluation_before_cp=before,
        evaluation_after_cp=after,
        centipawn_loss=loss,
    )


def _taxonomy(event, secondary=()):
    return ErrorClassification(
        ply=7,
        move_number=4,
        move_san=None,
        move_uci="",
        phase=GamePhase.MIDDLEGAME,
        severity=MoveClassification.BLUNDER,
        primary_type=event,
        secondary_types=secondary,
        confidence=ErrorConfidence.HIGH,
        centipawn_loss=250,
        critical_moment_type=None,
    )


def _facts(row=None, event=None, *, user_color=Color.WHITE, next_move=None):
    return build_move_explanation_facts(
        move_analysis=row or _row(),
        user_color=user_color,
        taxonomy=_taxonomy(event) if event else None,
        next_move_uci=next_move,
    )


@pytest.mark.parametrize(
    ("piece", "case", "expected"),
    [
        ("pawn", "nominative", "пешка"), ("pawn", "accusative", "пешку"),
        ("pawn", "genitive", "пешки"), ("knight", "nominative", "конь"),
        ("knight", "accusative", "коня"), ("bishop", "genitive", "слона"),
        ("rook", "accusative", "ладью"), ("rook", "genitive", "ладьи"),
        ("queen", "accusative", "ферзя"), ("king", "genitive", "короля"),
    ],
)
def test_controlled_russian_piece_grammar(piece, case, expected):
    assert russian_piece(piece, case) == expected


def test_hanging_piece_complete_partial_and_minimal_reduce_specificity():
    complete = _facts(
        _row("k7/8/2p5/8/8/2N5/8/7K w - - 0 1", "c3b5"),
        ErrorType.HANGING_PIECE,
    )
    partial = _facts(event=ErrorType.HANGING_PIECE)
    minimal = _facts()

    rich = generate_move_commentary(complete, detail_level="detailed")
    cautious = generate_move_commentary(partial)
    fallback = generate_move_commentary(minimal)

    assert "b5" in rich.summary and "кон" in rich.summary.lower()
    assert any("cxb5" in item for item in rich.details)
    assert "одн" in cautious.summary and "фигур" in cautious.summary
    assert "конь" not in cautious.summary.lower()
    assert fallback.intent_kind is CommentIntentKind.FALLBACK_EVALUATION


def test_mate_priority_over_hanging_piece_and_recommendation_keeps_mate_san():
    row = _row(
        "6k1/8/8/8/8/8/7Q/6K1 w - - 0 1",
        "h2h3",
        best="h2h7",
        before=0,
        after=-MATE_EVALUATION_THRESHOLD,
    )
    facts = _facts(row, ErrorType.HANGING_PIECE)
    result = generate_move_commentary(facts)
    assert result.intent_kind is CommentIntentKind.ALLOWED_MATE
    assert "мат" in result.summary
    assert result.recommendation and "Qh7+" in result.recommendation


def test_missed_mate_uses_persisted_transition_without_distance_claim():
    facts = _facts(
        _row(best="d2d4", before=MATE_EVALUATION_THRESHOLD, after=0),
        ErrorType.MISSED_MATE,
    )
    result = generate_move_commentary(facts)
    assert result.intent_kind is CommentIntentKind.MISSED_MATE
    assert "мат" in result.summary
    assert "мат в" not in (result.summary + (result.recommendation or "")).lower()


def test_missed_capture_names_only_validated_target_and_preserves_check_marker():
    row = _row("4k3/8/8/7r/8/8/8/3QK3 w - - 0 1", "d1d2", best="d1h5")
    result = generate_move_commentary(_facts(row, ErrorType.MISSED_CAPTURE))
    assert result.intent_kind is CommentIntentKind.MISSED_CAPTURE
    assert "ладью на h5" in result.summary
    assert "Qxh5+" in result.summary


def test_missed_check_never_claims_that_check_wins():
    row = _row("6k1/8/8/8/8/8/8/3R2K1 w - - 0 1", "d1d2", best="d1d8")
    result = generate_move_commentary(_facts(row, ErrorType.MISSED_CHECK))
    assert "Rd8+" in result.summary and "шах" in result.summary
    assert "выиг" not in result.summary.lower()


def test_fork_complete_names_targets_but_partial_does_not():
    row = _row("6k1/8/8/4n3/8/8/1Q1R3P/6K1 w - - 0 1", "h2h3")
    complete = generate_move_commentary(_facts(row, ErrorType.FORK, next_move="e5c4"))
    partial = generate_move_commentary(_facts(_row(), ErrorType.FORK))
    assert "ферзя" in complete.summary and "ладью" in complete.summary
    assert "вилк" in partial.summary or "двойное нападение" in partial.summary
    assert "ферз" not in partial.summary


def test_pin_complete_uses_piece_square_and_king_square():
    row = _row("4r1k1/8/8/8/8/4B3/4N3/4K3 w - - 0 1", "e3f4")
    result = generate_move_commentary(_facts(row, ErrorType.PIN), detail_level="detailed")
    assert "e2" in result.summary and "корол" in result.summary and "e1" in result.summary
    assert any("ладья на e8" in item.lower() for item in result.details)


def test_king_safety_prefers_concrete_castling_rights_fact():
    row = _row("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "e1f1")
    result = generate_move_commentary(_facts(row, ErrorType.KING_SAFETY))
    assert "рокиров" in result.summary
    assert "слаб" not in result.summary


def test_development_and_pawn_structure_use_only_existing_facts():
    fen, move = _before("1. e4 e5 2. Qh5")
    development = generate_move_commentary(_facts(_row(fen, move), ErrorType.DEVELOPMENT))
    pawn = generate_move_commentary(_facts(
        _row("6k1/8/8/8/2n5/3P4/2P5/6K1 w - - 0 1", "d3c4"),
        ErrorType.PAWN_STRUCTURE,
    ))
    assert "Ферз" in development.summary and "лёгкие фигуры" in development.summary
    assert "сдвоенные пешки" in pawn.summary


def test_bad_exchange_describes_immediate_capture_without_forced_future_loss():
    row = _row("r5k1/p7/8/8/8/8/8/R5BK w - - 0 1", "a1a7")
    result = generate_move_commentary(_facts(row, ErrorType.BAD_EXCHANGE), detail_level="detailed")
    assert "Rxa7" in result.summary and "пеш" in result.summary.lower()
    text = " ".join((result.summary, *result.details))
    assert "обязательно" not in text and "гарантирован" not in text


def test_secondary_event_never_replaces_primary_event():
    facts = build_move_explanation_facts(
        move_analysis=_row(),
        user_color=Color.WHITE,
        taxonomy=_taxonomy(ErrorType.DEVELOPMENT, secondary=(ErrorType.FORK,)),
    )
    intent = build_comment_intent(facts)
    assert intent.kind is CommentIntentKind.DEVELOPMENT


def test_minimal_fallback_prefers_concrete_capture_then_check_then_evaluation():
    capture = _facts(_row("4k3/8/8/7r/8/8/8/3QK3 w - - 0 1", "d1d2", best="d1h5"))
    check = _facts(_row("6k1/8/8/8/8/8/8/3R2K1 w - - 0 1", "d1d2", best="d1d8"))
    evaluation = _facts(_row(best=None, before=100, after=-200))
    assert build_comment_intent(capture).kind is CommentIntentKind.FALLBACK_BEST_CAPTURE
    assert build_comment_intent(check).kind is CommentIntentKind.FALLBACK_BEST_CHECK
    assert build_comment_intent(evaluation).kind is CommentIntentKind.FALLBACK_EVALUATION


def test_fallback_capture_does_not_invent_queen_when_target_is_rook():
    facts = _facts(_row("4k3/8/8/7r/8/8/8/3QK3 w - - 0 1", "d1d2", best="d1h5"))
    result = generate_move_commentary(facts)
    assert "ладью" in result.summary
    assert "ферз" not in result.summary.lower()


def test_user_pov_evaluation_language_for_black_uses_normalized_values():
    row = _row("4k3/8/8/8/8/8/P7/4K3 b - - 0 1", "e8d8", before=-100, after=200)
    facts = _facts(row, user_color=Color.BLACK)
    assert facts.evaluation.before_cp == 100 and facts.evaluation.after_cp == -200
    result = generate_move_commentary(facts)
    assert result.intent_kind is CommentIntentKind.FALLBACK_EVALUATION
    assert any(token in result.summary for token in ("сниз", "хуже", "соперника"))


@pytest.mark.parametrize(
    ("fen", "played", "best", "classification", "kind", "text"),
    [
        (chess.STARTING_FEN, "e2e4", "e2e4", MoveClassification.NORMAL, CommentIntentKind.POSITIVE_BEST, "точн"),
        ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "e1g1", None, MoveClassification.NORMAL, CommentIntentKind.POSITIVE_CASTLING, "короткую рокировку"),
        ("4k3/P7/8/8/8/8/8/4K3 w - - 0 1", "a7a8n", None, MoveClassification.NORMAL, CommentIntentKind.POSITIVE_PROMOTION, "коня"),
        ("4k3/8/8/8/8/8/4p3/3QK3 w - - 0 1", "d1e2", None, MoveClassification.NORMAL, CommentIntentKind.POSITIVE_CAPTURE, "пешку"),
        ("6k1/8/8/8/8/8/8/3R2K1 w - - 0 1", "d1d8", None, MoveClassification.NORMAL, CommentIntentKind.POSITIVE_CHECK, "rd8+"),
    ],
)
def test_positive_move_intents_are_factual(fen, played, best, classification, kind, text):
    result = generate_move_commentary(_facts(_row(fen, played, best=best, classification=classification, before=0, after=0, loss=0)))
    assert result.intent_kind is kind
    assert text in (result.headline + " " + result.summary).lower()
    assert result.recommendation is None


def test_en_passant_capture_commentary_names_pawn():
    fen, played = _before("1. e4 a6 2. e5 d5 3. exd6")
    result = generate_move_commentary(_facts(_row(fen, played, classification=MoveClassification.NORMAL, before=0, after=0)))
    assert result.intent_kind is CommentIntentKind.POSITIVE_CAPTURE
    assert "пешку" in result.summary


def test_short_standard_detailed_have_bounded_structure():
    facts = _facts(_row("k7/8/2p5/8/8/2N5/8/7K w - - 0 1", "c3b5"), ErrorType.HANGING_PIECE)
    short = generate_move_commentary(facts, detail_level="short")
    standard = generate_move_commentary(facts, detail_level="standard")
    detailed = generate_move_commentary(facts, detail_level="detailed")
    assert short.details == () and short.recommendation is None
    assert standard.details == ()
    assert detailed.details and len(detailed.details) <= 3


def test_template_ids_and_three_stage_pipeline_are_stable():
    facts = _facts()
    intent = build_comment_intent(facts)
    plan = build_comment_plan(intent)
    result = generate_move_commentary(facts)
    assert plan.template_id == result.template_id
    assert result.template_family == "fallback_evaluation.minimal.v2"
    assert result.variant_id
    assert result.intent_kind is intent.kind


def test_repeated_generation_is_fully_deterministic():
    facts = _facts(_row(best="d2d4"))
    assert len({generate_move_commentary(facts) for _ in range(100)}) == 1


def test_insufficient_fallback_does_not_invent_chess_nouns():
    facts = _facts(_row(best=None, before=None, after=None, loss=None))
    result = generate_move_commentary(facts)
    assert result.intent_kind is CommentIntentKind.FALLBACK_INSUFFICIENT
    assert result.recommendation is None
    assert all(word not in result.summary.lower() for word in ("ферз", "ладь", "кон", "слон"))


def test_module_has_no_engine_network_database_or_random_dependency():
    source = Path(__import__("app.services.move_commentary", fromlist=["x"]).__file__).read_text()
    forbidden = ("Stockfish", "requests", "urllib", "Session", "from random", "import random", "time.time")
    assert all(token not in source for token in forbidden)


def test_commentary_models_are_immutable():
    result = generate_move_commentary(_facts())
    with pytest.raises(Exception):
        result.headline = "changed"


def test_invalid_detail_level_fails_explicitly():
    with pytest.raises(ValueError):
        build_comment_intent(_facts(), detail_level="essay")


def test_stable_selector_has_versioned_known_result():
    seed = "7|5|fallback_evaluation|blunder|e2e4|g1f3||minimal"
    assert COMMENTARY_VERSION == "2"
    assert stable_variant_index(seed, "evaluation", 13) == 2
    assert stable_variant_index(seed, "evaluation", 13, version="3") != 2


def test_adjacent_ply_seeds_distribute_variants_without_mutable_history():
    base = _facts(_row(best="g1f3", before=30, after=-20))
    variants = {
        generate_move_commentary(replace(base, game_id=44, ply=ply)).variant_id
        for ply in range(1, 41)
    }
    assert len(variants) >= 8


def test_standard_includes_important_consequence_and_deduplicates_best_move():
    hanging = _facts(
        _row("k7/8/2p5/8/8/2N5/8/7K w - - 0 1", "c3b5", best="c3a4"),
        ErrorType.HANGING_PIECE,
    )
    standard = generate_move_commentary(hanging)
    assert "b5" in standard.summary and "cxb5" in standard.summary

    capture = _facts(
        _row("4k3/8/8/7r/8/8/8/3QK3 w - - 0 1", "d1d2", best="d1h5"),
        ErrorType.MISSED_CAPTURE,
    )
    comment = generate_move_commentary(capture)
    assert comment.summary.count("Qxh5+") == 1
    assert comment.recommendation is None


def test_missing_best_move_never_renders_none():
    result = generate_move_commentary(_facts(_row(best=None, before=30, after=-50)))
    text = " ".join((result.headline, result.summary, *(result.details), result.recommendation or ""))
    assert "None" not in text


def test_synthetic_context_matrix_has_compositional_diversity():
    base = _facts(_row(best="g1f3", before=120, after=20))
    phases = (GamePhase.OPENING, GamePhase.MIDDLEGAME, GamePhase.ENDGAME)
    deltas = ((40, 0), (150, 20), (400, -100), (120, -80))
    outputs = set()
    variants = set()
    for identity in range(1, 501):
        before, after = deltas[identity % len(deltas)]
        facts = replace(
            base,
            game_id=identity // 80 + 1,
            ply=identity,
            phase=phases[identity % len(phases)],
            evaluation=replace(base.evaluation, before_cp=before, after_cp=after),
        )
        comment = generate_move_commentary(facts)
        outputs.add((comment.summary, comment.recommendation))
        variants.add(comment.variant_id)
    assert len(outputs) >= 80
    assert len(variants) >= 100


def test_partial_hanging_variants_never_add_capture_or_specific_piece():
    base = _facts(event=ErrorType.HANGING_PIECE)
    for ply in range(1, 50):
        comment = generate_move_commentary(replace(base, game_id=9, ply=ply))
        text = " ".join((comment.summary, *comment.details))
        assert "x" not in text
        assert all(noun not in text.lower() for noun in ("ферз", "ладь", "конь", "слон"))


def test_selector_is_stable_across_processes_and_python_hash_seeds():
    code = (
        "from app.services.move_commentary import stable_variant_index;"
        "print(stable_variant_index('same-move','reason',17))"
    )
    values = []
    for hash_seed in ("1", "999"):
        environment = dict(os.environ, PYTHONHASHSEED=hash_seed)
        values.append(subprocess.check_output([sys.executable, "-c", code], env=environment, text=True).strip())
    assert values[0] == values[1]


def test_evaluation_wording_does_not_claim_opponent_advantage_without_sign_transition():
    base = _facts(_row(best=None, before=500, after=300))
    for ply in range(1, 80):
        text = generate_move_commentary(replace(base, game_id=2, ply=ply)).summary
        assert "в пользу соперника" not in text


def test_generated_text_has_clean_plain_text_punctuation():
    base = _facts(_row(best="g1f3", before=120, after=20))
    for ply in range(1, 100):
        result = generate_move_commentary(replace(base, game_id=4, ply=ply), detail_level="detailed")
        text = " ".join((result.headline, result.summary, *result.details, result.recommendation or ""))
        assert "  " not in text and ".." not in text and " ," not in text
        assert all(marker not in text for marker in ("**", "`", "🙂", "⭐"))


def test_template_family_is_typed_and_immutable():
    family = CommentTemplateFamily("sample", ("Заголовок",), ("Причина",))
    assert family.family_id == "sample"
    with pytest.raises(Exception):
        family.family_id = "changed"
