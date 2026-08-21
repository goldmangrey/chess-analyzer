"""Deterministic Russian commentary rendered only from validated move facts.

This module deliberately has no database, engine, network, or API dependencies.
Semantic selection is separated from wording so Step 3.7.5 can add variants
without changing which chess claims are allowed.
"""

from dataclasses import dataclass
from enum import Enum
import hashlib
from typing import Literal

from app.models import ErrorType, GamePhase, MoveClassification
from app.services.move_explanation_facts import MoveExplanationFacts, MoveFact, PieceOnSquare


DetailLevel = Literal["short", "standard", "detailed"]
CommentTone = Literal["positive", "neutral", "corrective", "critical"]
COMMENTARY_VERSION = "2"
EVALUATION_EQUAL_BAND_CP = 50


class CommentIntentKind(str, Enum):
    HANGING_PIECE = "hanging_piece"
    MISSED_CAPTURE = "missed_capture"
    MISSED_CHECK = "missed_check"
    MISSED_MATE = "missed_mate"
    ALLOWED_MATE = "allowed_mate"
    FORK = "fork"
    PIN = "pin"
    KING_SAFETY = "king_safety"
    DEVELOPMENT = "development"
    PAWN_STRUCTURE = "pawn_structure"
    BAD_EXCHANGE = "bad_exchange"
    TACTICAL_PATTERN = "tactical_pattern"
    POSITIVE_BEST = "positive_best"
    POSITIVE_CAPTURE = "positive_capture"
    POSITIVE_CHECK = "positive_check"
    POSITIVE_CASTLING = "positive_castling"
    POSITIVE_PROMOTION = "positive_promotion"
    FALLBACK_BEST_CAPTURE = "fallback_best_capture"
    FALLBACK_BEST_CHECK = "fallback_best_check"
    FALLBACK_MATERIAL = "fallback_material"
    FALLBACK_EVALUATION = "fallback_evaluation"
    FALLBACK_BEST_MOVE = "fallback_best_move"
    FALLBACK_INSUFFICIENT = "fallback_insufficient"


@dataclass(frozen=True)
class RussianPieceForms:
    nominative: str
    accusative: str
    genitive: str
    instrumental: str


RUSSIAN_PIECES: dict[str, RussianPieceForms] = {
    "pawn": RussianPieceForms("пешка", "пешку", "пешки", "пешкой"),
    "knight": RussianPieceForms("конь", "коня", "коня", "конём"),
    "bishop": RussianPieceForms("слон", "слона", "слона", "слоном"),
    "rook": RussianPieceForms("ладья", "ладью", "ладьи", "ладьёй"),
    "queen": RussianPieceForms("ферзь", "ферзя", "ферзя", "ферзём"),
    "king": RussianPieceForms("король", "короля", "короля", "королём"),
}


def russian_piece(piece: str, case: Literal["nominative", "accusative", "genitive", "instrumental"] = "nominative") -> str:
    """Return a controlled chess-piece form; unknown values fail generically."""
    forms = RUSSIAN_PIECES.get(piece)
    return getattr(forms, case) if forms else "фигура"


@dataclass(frozen=True)
class CommentIntent:
    game_id: int | None
    ply: int
    kind: CommentIntentKind
    severity: MoveClassification | None
    tone: CommentTone
    played_move: MoveFact | None
    best_move: MoveFact | None
    reason_fact: object | None
    consequence_fact: object | None
    recommendation_fact: MoveFact | None
    evaluation_fact: object
    detail_level: DetailLevel
    fact_completeness: str
    phase: GamePhase | None
    primary_event: ErrorType | None


@dataclass(frozen=True)
class CommentPlan:
    template_family: str
    variant_id: str
    template_id: str
    headline: str
    reason: str | None = None
    consequence: str | None = None
    recommendation: str | None = None
    evaluation: str | None = None


@dataclass(frozen=True)
class MoveCommentary:
    headline: str
    summary: str
    details: tuple[str, ...]
    recommendation: str | None
    intent_kind: CommentIntentKind
    detail_level: DetailLevel
    fact_completeness: str
    template_id: str
    template_family: str
    variant_id: str


@dataclass(frozen=True)
class CommentTemplateFamily:
    """Immutable compositional fragment bank for one semantic family."""

    family_id: str
    headlines: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    consequences: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()


@dataclass(frozen=True)
class SelectedFragment:
    text: str
    index: int


def stable_variant_index(seed: str, slot: str, variant_count: int, *, version: str = COMMENTARY_VERSION) -> int:
    """Process-independent selector; built-in hash and mutable state are forbidden."""
    if variant_count <= 0:
        raise ValueError("variant_count must be positive")
    payload = f"{version}|{seed}|{slot}".encode()
    digest = hashlib.blake2b(payload, digest_size=8, person=b"chess-cmt").digest()
    return int.from_bytes(digest, "big") % variant_count


def _intent_seed(intent: CommentIntent) -> str:
    return "|".join(
        (
            str(intent.game_id or 0),
            str(intent.ply),
            intent.kind.value,
            intent.severity.value if intent.severity else "",
            intent.played_move.uci if intent.played_move else "",
            intent.best_move.uci if intent.best_move else "",
            intent.primary_event.value if intent.primary_event else "",
            intent.fact_completeness,
        )
    )


def _select(intent: CommentIntent, slot: str, variants: tuple[str, ...]) -> SelectedFragment:
    index = stable_variant_index(_intent_seed(intent), slot, len(variants))
    return SelectedFragment(variants[index], index)


_EVENT_KINDS = {
    ErrorType.HANGING_PIECE: CommentIntentKind.HANGING_PIECE,
    ErrorType.MISSED_CAPTURE: CommentIntentKind.MISSED_CAPTURE,
    ErrorType.MISSED_CHECK: CommentIntentKind.MISSED_CHECK,
    ErrorType.MISSED_MATE: CommentIntentKind.MISSED_MATE,
    ErrorType.ALLOWED_MATE: CommentIntentKind.ALLOWED_MATE,
    ErrorType.FORK: CommentIntentKind.FORK,
    ErrorType.PIN: CommentIntentKind.PIN,
    ErrorType.KING_SAFETY: CommentIntentKind.KING_SAFETY,
    ErrorType.DEVELOPMENT: CommentIntentKind.DEVELOPMENT,
    ErrorType.PAWN_STRUCTURE: CommentIntentKind.PAWN_STRUCTURE,
    ErrorType.BAD_EXCHANGE: CommentIntentKind.BAD_EXCHANGE,
    ErrorType.TACTICAL_PATTERN: CommentIntentKind.TACTICAL_PATTERN,
    ErrorType.SKEWER: CommentIntentKind.TACTICAL_PATTERN,
    ErrorType.BACK_RANK: CommentIntentKind.TACTICAL_PATTERN,
}


def _tone(classification: MoveClassification | None, positive: bool = False) -> CommentTone:
    if positive:
        return "positive"
    if classification is MoveClassification.BLUNDER:
        return "critical"
    if classification in {MoveClassification.MISTAKE, MoveClassification.INACCURACY}:
        return "corrective"
    return "neutral"


def _event_detail(facts: MoveExplanationFacts) -> object | None:
    return {
        ErrorType.HANGING_PIECE: facts.hanging_piece,
        ErrorType.MISSED_CAPTURE: facts.missed_capture,
        ErrorType.MISSED_CHECK: facts.missed_check,
        ErrorType.FORK: facts.fork,
        ErrorType.PIN: facts.pin,
        ErrorType.KING_SAFETY: facts.king_safety,
        ErrorType.DEVELOPMENT: facts.development,
        ErrorType.PAWN_STRUCTURE: facts.pawn_structure,
        ErrorType.BAD_EXCHANGE: facts.bad_exchange,
    }.get(facts.primary_event)


def build_comment_intent(facts: MoveExplanationFacts, *, detail_level: DetailLevel = "standard") -> CommentIntent:
    """Choose the strongest supported semantic intent without rendering text."""
    if detail_level not in {"short", "standard", "detailed"}:
        raise ValueError(f"Unsupported commentary detail level: {detail_level}")

    # Persisted mate transitions outrank every taxonomy label.
    if facts.allowed_mate or facts.evaluation.opponent_has_forced_mate:
        kind = CommentIntentKind.ALLOWED_MATE
        reason = facts.evaluation
    elif facts.missed_mate or facts.evaluation.missed_mate:
        kind = CommentIntentKind.MISSED_MATE
        reason = facts.evaluation
    elif facts.primary_event in _EVENT_KINDS:
        kind = _EVENT_KINDS[facts.primary_event]
        reason = _event_detail(facts)
    elif facts.comparison and facts.comparison.is_engine_best:
        kind = CommentIntentKind.POSITIVE_BEST
        reason = facts.played_move
    elif facts.played_move and facts.played_move.is_promotion:
        kind = CommentIntentKind.POSITIVE_PROMOTION
        reason = facts.played_move
    elif facts.played_move and facts.played_move.is_castling:
        kind = CommentIntentKind.POSITIVE_CASTLING
        reason = facts.played_move
    elif facts.classification is MoveClassification.NORMAL and facts.played_move and facts.played_move.is_capture:
        kind = CommentIntentKind.POSITIVE_CAPTURE
        reason = facts.played_move
    elif facts.classification is MoveClassification.NORMAL and facts.played_move and facts.played_move.is_check:
        kind = CommentIntentKind.POSITIVE_CHECK
        reason = facts.played_move
    elif facts.best_move and facts.comparison and facts.comparison.best_is_capture and not facts.comparison.played_is_capture:
        kind = CommentIntentKind.FALLBACK_BEST_CAPTURE
        reason = facts.best_move
    elif facts.best_move and facts.comparison and facts.comparison.best_gives_check and not facts.comparison.played_gives_check:
        kind = CommentIntentKind.FALLBACK_BEST_CHECK
        reason = facts.best_move
    elif facts.best_move and facts.comparison and facts.comparison.best_move_wins_more_material:
        kind = CommentIntentKind.FALLBACK_MATERIAL
        reason = facts.comparison
    elif _evaluation_worsened(facts):
        kind = CommentIntentKind.FALLBACK_EVALUATION
        reason = facts.evaluation
    elif facts.best_move and (not facts.played_move or facts.best_move.uci != facts.played_move.uci):
        kind = CommentIntentKind.FALLBACK_BEST_MOVE
        reason = facts.best_move
    else:
        kind = CommentIntentKind.FALLBACK_INSUFFICIENT
        reason = None

    recommendation = facts.best_move
    if facts.played_move and recommendation and facts.played_move.uci == recommendation.uci:
        recommendation = None
    return CommentIntent(
        game_id=facts.game_id,
        ply=facts.ply,
        kind=kind,
        severity=facts.classification,
        tone=_tone(facts.classification, kind.value.startswith("positive_")),
        played_move=facts.played_move,
        best_move=facts.best_move,
        reason_fact=reason,
        consequence_fact=_event_detail(facts),
        recommendation_fact=recommendation,
        evaluation_fact=facts.evaluation,
        detail_level=detail_level,
        fact_completeness=facts.fact_completeness,
        phase=facts.phase,
        primary_event=facts.primary_event,
    )


def _evaluation_worsened(facts: MoveExplanationFacts) -> bool:
    evaluation = facts.evaluation
    if evaluation.mate_after == "against_user" and evaluation.mate_before != "against_user":
        return True
    return bool(
        evaluation.before_cp is not None
        and evaluation.after_cp is not None
        and evaluation.after_cp < evaluation.before_cp
    )


def _recommendation_variants(move: MoveFact | None, phase: GamePhase | None) -> tuple[str, ...]:
    if move is None:
        return ()
    variants = [
        f"Точнее было сыграть {move.san}.",
        f"Сильнее было {move.san}.",
        f"Лучшее продолжение здесь — {move.san}.",
        f"В этой позиции точнее {move.san}.",
    ]
    if phase is GamePhase.OPENING:
        variants.append(f"В дебюте точнее было сыграть {move.san}.")
    elif phase is GamePhase.MIDDLEGAME:
        variants.append(f"В миттельшпиле точнее было {move.san}.")
    elif phase is GamePhase.ENDGAME:
        variants.append(f"В эндшпиле точнее было сыграть {move.san}.")
    return tuple(variants)


def _capture_sentence(move: MoveFact, *, missed: bool = False) -> str | None:
    victim = move.captured_piece
    if victim is None:
        return None
    if missed:
        return f"Ходом {move.san} можно было забрать {russian_piece(victim.piece, 'accusative')} на {victim.square}."
    return f"Ходом {move.san} вы забрали {russian_piece(victim.piece, 'accusative')} на {victim.square}."


def _join_targets(targets: tuple[PieceOnSquare, ...]) -> str:
    labels = [f"{russian_piece(target.piece, 'accusative')} на {target.square}" for target in targets[:2]]
    return " и ".join(labels)


def _linked_form(piece: str) -> str:
    return "связана" if piece in {"pawn", "rook"} else "связан"


def _evaluation_variants(intent: CommentIntent) -> tuple[str, ...]:
    facts = intent.evaluation_fact
    before = getattr(facts, "before_cp", None)
    after = getattr(facts, "after_cp", None)
    if before is None or after is None or after >= before:
        return ()
    delta = before - after
    phase = {
        GamePhase.OPENING: "В дебюте",
        GamePhase.MIDDLEGAME: "В миттельшпиле",
        GamePhase.ENDGAME: "В эндшпиле",
    }.get(intent.phase)
    crossed_against = before >= -EVALUATION_EQUAL_BAND_CP and after < -EVALUATION_EQUAL_BAND_CP
    lost_advantage = before > EVALUATION_EQUAL_BAND_CP and after <= EVALUATION_EQUAL_BAND_CP
    if delta >= 300:
        variants = [
            "Оценка позиции резко снизилась.",
            "После хода оценка позиции существенно снизилась.",
            "Этот ход привёл к резкому падению оценки.",
            "Позиция стала оцениваться заметно хуже.",
            "Оценка после хода резко снизилась.",
        ]
    elif delta >= 100:
        variants = [
            "Оценка позиции заметно ухудшилась.",
            "После хода позиция стала оцениваться хуже.",
            "Этот ход заметно снизил оценку позиции.",
            "Оценка после хода ощутимо снизилась.",
            "Позиционная оценка после этого решения заметно снизилась.",
        ]
    else:
        variants = [
            "Оценка позиции немного ухудшилась.",
            "После хода оценка слегка снизилась.",
            "Этот ход немного снизил оценку позиции.",
            "Позиция стала оцениваться чуть хуже.",
            "Оценка после хода слегка снизилась.",
            "После этого решения оценка стала немного ниже.",
        ]
    if lost_advantage:
        variants.extend((
            "После этого хода часть преимущества исчезла.",
            "Ход уменьшил имевшееся преимущество.",
        ))
    if crossed_against:
        variants.extend((
            "После хода оценка стала в пользу соперника.",
            "Оценка перешла от равной позиции к преимуществу соперника.",
        ))
    if intent.played_move and intent.best_move:
        if intent.played_move.piece == intent.best_move.piece:
            variants.extend((
                f"Этой же фигурой точнее было сыграть {intent.best_move.san}.",
                f"Точнее было выбрать другой ход той же фигурой — {intent.best_move.san}.",
            ))
        else:
            variants.extend((
                f"Вместо сыгранной фигуры точнее было сыграть {russian_piece(intent.best_move.piece, 'instrumental')}: {intent.best_move.san}.",
                f"Более точное продолжение начиналось ходом {intent.best_move.san} другой фигурой.",
            ))
        if intent.played_move.is_capture and not intent.best_move.is_capture:
            variants.append(f"Вместо взятия точнее было сыграть {intent.best_move.san}.")
        if intent.played_move.is_check and not intent.best_move.is_check:
            variants.append(f"Вместо шаха точнее было сыграть {intent.best_move.san}.")
    if (
        intent.played_move
        and intent.best_move
        and not intent.played_move.is_capture
        and not intent.best_move.is_capture
    ):
        variants.append("Материал сразу не изменился, но оценка позиции снизилась.")
    if phase:
        variants.extend((
            f"{phase} этот ход немного уступает более точному продолжению." if delta < 100 else f"{phase} оценка после хода заметно снизилась.",
            f"{phase} позиция после этого решения оценивается хуже.",
        ))
    return tuple(dict.fromkeys(variants))


def build_comment_plan(intent: CommentIntent) -> CommentPlan:
    """Build factual Russian clauses; no clause may introduce a new chess fact."""
    kind = intent.kind
    complete = intent.fact_completeness == "complete"
    family = f"{kind.value}.{intent.fact_completeness}.v{COMMENTARY_VERSION}"
    selected_ids: list[str] = []

    def pick(slot: str, variants: tuple[str, ...]) -> str:
        selected = _select(intent, slot, variants)
        selected_ids.append(f"{slot[0]}{selected.index}")
        return selected.text

    recommendation_variants = _recommendation_variants(intent.recommendation_fact, intent.phase)
    recommendation = pick("recommendation", recommendation_variants) if recommendation_variants else None
    headline = "Комментарий к ходу"
    reason = consequence = evaluation = None

    if kind is CommentIntentKind.ALLOWED_MATE:
        headline = pick("headline", ("Вы допустили форсированный мат", "Появилась угроза форсированного мата"))
        reason = pick("reason", (
            "После этого хода у соперника появляется форсированный мат.",
            "Ход допускает форсированный мат со стороны соперника.",
            "После хода позиция допускает матующую последовательность соперника.",
        ))
    elif kind is CommentIntentKind.MISSED_MATE:
        headline = pick("headline", ("Был доступен мат", "Матующая возможность упущена"))
        mate_move = intent.best_move
        variants = [
            "В этой позиции была возможность форсированного мата.",
            "Здесь существовало матующее продолжение.",
            "В позиции был доступен форсированный мат.",
        ]
        if mate_move and mate_move.san.endswith("#"):
            variants.append(f"Ход {mate_move.san} сразу ставил мат.")
        reason = pick("reason", tuple(variants))
    elif kind is CommentIntentKind.HANGING_PIECE:
        detail = intent.reason_fact
        if complete and detail is not None:
            piece = detail.piece
            headline = pick("headline", ("Вы оставили фигуру под ударом", "Фигура оказалась атакована", "Появилось доступное взятие фигуры"))
            piece_nom = russian_piece(piece.piece)
            piece_acc = russian_piece(piece.piece, "accusative")
            reason = pick("reason", (
                f"{piece_nom.capitalize()} на {piece.square} остаётся под ударом.",
                f"После хода {piece_nom} на {piece.square} оказывается атакован.",
                f"Ход оставляет {piece_acc} на {piece.square} под боем.",
                f"На поле {piece.square} {piece_nom} становится доступной целью.",
            ))
            if detail.opponent_capture_moves:
                capture = detail.opponent_capture_moves[0]
                consequence = pick("consequence", (
                    f"Соперник может забрать {piece_acc} ходом {capture}.",
                    f"Взятие {capture} против {russian_piece(piece.piece, 'genitive')} теперь доступно сопернику.",
                    f"У соперника появляется легальное взятие {capture}.",
                    f"Ход {capture} позволяет сопернику забрать {piece_acc}.",
                ))
        else:
            headline = pick("headline", ("Фигура оказалась под ударом", "Возникло нападение на фигуру"))
            reason = pick("reason", ("После этого хода одна из фигур оказывается под ударом.", "Ход оставляет одну из фигур атакованной."))
    elif kind is CommentIntentKind.MISSED_CAPTURE:
        detail = intent.reason_fact
        headline = pick("headline", ("Вы упустили взятие", "Было доступно взятие", "Возможность взятия не использована"))
        if complete and detail is not None:
            target = russian_piece(detail.target.piece, "accusative")
            san = detail.available_move.san
            reason = pick("reason", (
                f"Можно было забрать {target} на {detail.target.square} ходом {san}.",
                f"В позиции было доступно взятие {san}, которое забирало {target}.",
                f"Ход {san} позволял сразу взять {target}.",
                f"На {detail.target.square} можно было взять {target} ходом {san}.",
            ))
        else:
            reason = pick("reason", ("В позиции была более сильная возможность взятия.", "Доступное взятие осталось неиспользованным."))
    elif kind is CommentIntentKind.MISSED_CHECK:
        headline = pick("headline", ("Можно было дать шах", "Шахующая возможность упущена", "Был доступен шах"))
        if complete and intent.reason_fact is not None:
            san = intent.reason_fact.san
            reason = pick("reason", (f"Ход {san} давал шах.", f"Можно было дать шах ходом {san}.", f"В позиции был доступен шах {san}.", f"Точнее было сыграть {san} с шахом."))
        else:
            reason = pick("reason", ("В позиции была возможность дать шах.", "Доступный шах остался неиспользованным."))
    elif kind is CommentIntentKind.FORK:
        detail = intent.reason_fact
        headline = pick("headline", ("Возникла тактическая вилка", "Появилось двойное нападение", "Две фигуры оказались под атакой"))
        if complete and detail is not None:
            targets = _join_targets(detail.targets)
            attacker = russian_piece(detail.attacker.piece)
            reason = pick("reason", (
                f"{attacker.capitalize()} на {detail.attacker.square} одновременно атакует {targets}.",
                f"Возникает вилка: {attacker} атакует {targets}.",
                f"Ход создаёт двойное нападение на {targets}.",
            ))
        else:
            reason = pick("reason", ("В позиции возникает тактическая вилка.", "После хода появляется двойное нападение."))
    elif kind is CommentIntentKind.PIN:
        detail = intent.reason_fact
        headline = pick("headline", ("Фигура оказалась связана", "Возникла связка", "Появилась связанная фигура"))
        if complete and detail is not None:
            pinned = detail.pinned_piece
            piece = russian_piece(pinned.piece)
            reason = pick("reason", (f"{piece.capitalize()} на {pinned.square} {_linked_form(pinned.piece)} с королём на {detail.king_square}.", f"Возникает связка {russian_piece(pinned.piece, 'genitive')} на {pinned.square} с королём.", f"Фигура на {pinned.square} связана с королём на {detail.king_square}."))
            if detail.attacking_sliders:
                slider = detail.attacking_sliders[0]
                consequence = pick("consequence", (f"Связку создаёт {russian_piece(slider.piece)} на {slider.square}.", f"Атакующая фигура — {russian_piece(slider.piece)} на {slider.square}."))
        else:
            reason = pick("reason", ("После этого хода в позиции возникает связка.", "Одна из фигур оказывается связана."))
    elif kind is CommentIntentKind.KING_SAFETY:
        detail = intent.reason_fact
        headline = pick("headline", ("Ход затронул положение короля", "Изменились условия безопасности короля"))
        if detail is not None and detail.castling_rights_before and not detail.castling_rights_after:
            reason = pick("reason", ("После этого хода вы теряете право на рокировку.", "Ход лишает вас возможности рокироваться.", "Право на рокировку после хода теряется."))
        elif detail is not None and detail.king_in_check_after:
            reason = pick("reason", ("После этого хода король оказывается под шахом.", "Ход оставляет короля под шахом."))
        elif detail is not None and detail.pawn_shield_after < detail.pawn_shield_before:
            reason = pick("reason", ("Пешечное прикрытие перед королём стало менее плотным.", "После хода перед королём осталось меньше пешечного прикрытия."))
        else:
            reason = "В этом ходе проблема связана с безопасностью короля."
    elif kind is CommentIntentKind.DEVELOPMENT:
        detail = intent.reason_fact
        headline = pick("headline", ("Ход связан с развитием фигур", "Развитие фигур требует более точного решения"))
        if detail is not None and detail.queen_moved and detail.undeveloped_minor_pieces_before:
            reason = pick("reason", ("Ферзь выходит, пока лёгкие фигуры ещё не развиты.", "Ход ферзём сделан до завершения развития лёгких фигур.", f"После хода ферзём неразвитыми остаются лёгкие фигуры: {detail.undeveloped_minor_pieces_before}."))
        elif detail is not None and detail.piece_returned_to_origin:
            reason = pick("reason", ("Фигура вернулась на исходное поле.", "Ход возвращает фигуру на её начальное поле."))
        else:
            reason = "В этом ходе проблема связана с развитием фигур."
    elif kind is CommentIntentKind.PAWN_STRUCTURE:
        detail = intent.reason_fact
        headline = pick("headline", ("Изменилась пешечная структура", "Ход изменил расположение пешек"))
        if detail is not None and detail.doubled_after > detail.doubled_before:
            reason = pick("reason", ("После хода появляются сдвоенные пешки.", "Ход создаёт сдвоенные пешки."))
        elif detail is not None and detail.isolated_after > detail.isolated_before:
            reason = pick("reason", ("После хода появляется изолированная пешка.", "Ход оставляет одну из пешек изолированной."))
        elif detail is not None and detail.pawn_islands_after > detail.pawn_islands_before:
            reason = pick("reason", ("Количество пешечных островков увеличилось.", "После хода пешки образуют больше отдельных групп."))
        else:
            reason = "В этом ходе проблема связана с пешечной структурой."
    elif kind is CommentIntentKind.BAD_EXCHANGE:
        headline = pick("headline", ("Вы выбрали этот размен", "Произошёл материальный размен", "Ход привёл к размену фигур"))
        move = intent.played_move
        if complete and move and move.captured_piece:
            mover = russian_piece(move.piece)
            victim = russian_piece(move.captured_piece.piece, "accusative")
            reason = pick("reason", (f"{mover.capitalize()} забирает {victim}.", f"Ход {move.san} выполняет взятие {russian_piece(move.captured_piece.piece, 'genitive')}.", f"При ходе {move.san} {mover} берёт {victim}."))
            if intent.detail_level == "detailed":
                consequence = f"Немедленно снятая фигура имеет номинальную ценность {move.captured_piece.value}."
        else:
            reason = "В этом ходе проблема связана с выбором размена."
    elif kind is CommentIntentKind.TACTICAL_PATTERN:
        headline = pick("headline", ("В позиции была тактическая возможность", "Ход связан с тактическим моментом"))
        if intent.best_move and intent.best_move.is_capture and intent.best_move.captured_piece:
            reason = _capture_sentence(intent.best_move, missed=True)
        elif intent.best_move and intent.best_move.is_check:
            reason = f"В позиции был доступен шах {intent.best_move.san}."
        else:
            reason = "Тактический мотив известен, но конкретная комбинация не подтверждена доступными фактами."
    elif kind is CommentIntentKind.POSITIVE_BEST:
        headline = pick("headline", ("Вы нашли лучший ход", "Это наиболее точное продолжение", "Вы сыграли лучший ход в позиции"))
        move = intent.played_move
        if move and move.is_capture and move.captured_piece:
            victim = russian_piece(move.captured_piece.piece, "accusative")
            reason = pick("reason", (f"Ход {move.san} забирает {victim}.", f"Лучший ход одновременно выполняет взятие {victim}."))
        elif move and move.is_check:
            reason = pick("reason", (f"Ход {move.san} даёт шах.", "Лучший ход одновременно даёт шах."))
    elif kind is CommentIntentKind.POSITIVE_PROMOTION:
        headline = "Пешка дошла до превращения"
        move = intent.played_move
        if move and move.promotion_piece:
            promoted = russian_piece(move.promotion_piece, "accusative")
            reason = pick("reason", (f"Пешка превратилась в {promoted}.", f"Ход {move.san} завершает превращение пешки в {promoted}."))
    elif kind is CommentIntentKind.POSITIVE_CASTLING:
        move = intent.played_move
        side = "короткую" if move and move.castling_side == "kingside" else "длинную"
        headline = "Вы сделали рокировку"
        side_nom = "короткая" if move and move.castling_side == "kingside" else "длинная"
        reason = pick("reason", (f"Вы сделали {side} рокировку.", f"Ходом {move.san if move else ''} выполнена {side_nom} рокировка."))
    elif kind is CommentIntentKind.POSITIVE_CAPTURE:
        headline = "Вы выполнили взятие"
        reason = _capture_sentence(intent.played_move) if intent.played_move else None
    elif kind is CommentIntentKind.POSITIVE_CHECK:
        headline = "Вы дали шах"
        reason = f"Ход {intent.played_move.san} даёт шах." if intent.played_move else None
    elif kind is CommentIntentKind.FALLBACK_BEST_CAPTURE:
        headline = "Была возможность взятия"
        reason = _capture_sentence(intent.best_move, missed=True) if intent.best_move else None
    elif kind is CommentIntentKind.FALLBACK_BEST_CHECK:
        headline = "Можно было дать шах"
        reason = f"Сильнее было дать шах ходом {intent.best_move.san}." if intent.best_move else None
    elif kind is CommentIntentKind.FALLBACK_MATERIAL:
        headline = "Можно было получить больше материала"
        reason = f"Ход {intent.best_move.san} сразу забирал больше материала." if intent.best_move else None
    elif kind is CommentIntentKind.FALLBACK_EVALUATION:
        headline = pick("headline", ("Оценка позиции снизилась", "Ход оказался менее точным", "Было более точное продолжение"))
        variants = _evaluation_variants(intent)
        evaluation = pick("evaluation", variants) if variants else None
    elif kind is CommentIntentKind.FALLBACK_BEST_MOVE:
        headline = "Было более точное продолжение"
    else:
        headline = "Недостаточно данных для точного объяснения"
        reason = "Доступных фактов недостаточно, чтобы надёжно объяснить этот ход."
        recommendation = None

    # Recommendation is useful after errors/fallbacks, never after positive intents.
    if kind.value.startswith("positive_"):
        recommendation = None
    elif kind in {
        CommentIntentKind.MISSED_CAPTURE,
        CommentIntentKind.MISSED_CHECK,
        CommentIntentKind.FALLBACK_BEST_CAPTURE,
        CommentIntentKind.FALLBACK_BEST_CHECK,
        CommentIntentKind.FALLBACK_MATERIAL,
    }:
        # The concrete best move is already present in the explanation.
        recommendation = None
    elif (
        recommendation
        and intent.recommendation_fact
        and intent.recommendation_fact.san in " ".join(value for value in (reason, consequence, evaluation) if value)
    ):
        recommendation = None
    variant_id = ".".join(selected_ids) or "base0"
    return CommentPlan(
        template_family=family,
        variant_id=variant_id,
        template_id=f"{family}.{variant_id}",
        headline=headline,
        reason=reason,
        consequence=consequence,
        recommendation=recommendation,
        evaluation=evaluation,
    )


def render_commentary_ru(plan: CommentPlan, intent: CommentIntent) -> MoveCommentary:
    """Render deterministic V2 output with bounded information density."""
    clauses = tuple(value for value in (plan.reason, plan.consequence, plan.evaluation) if value)
    if intent.detail_level == "short":
        summary = clauses[0] if clauses else plan.headline + "."
        details: tuple[str, ...] = ()
        recommendation = None
    elif intent.detail_level == "standard":
        visible = clauses[:2]
        summary = " ".join(visible) if visible else plan.headline + "."
        details = ()
        recommendation = plan.recommendation
    else:
        summary = clauses[0] if clauses else plan.headline + "."
        details = clauses[1:]
        recommendation = plan.recommendation
    return MoveCommentary(
        headline=plan.headline,
        summary=summary,
        details=details,
        recommendation=recommendation,
        intent_kind=intent.kind,
        detail_level=intent.detail_level,
        fact_completeness=intent.fact_completeness,
        template_id=plan.template_id,
        template_family=plan.template_family,
        variant_id=plan.variant_id,
    )


def generate_move_commentary(
    facts: MoveExplanationFacts,
    *,
    detail_level: DetailLevel = "standard",
) -> MoveCommentary:
    intent = build_comment_intent(facts, detail_level=detail_level)
    return render_commentary_ru(build_comment_plan(intent), intent)
