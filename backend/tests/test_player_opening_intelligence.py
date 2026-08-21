from types import SimpleNamespace

from app.models import Color
from app.services.player_opening_intelligence import build_player_opening_intelligence


def game(game_id, *, color="white", result="win", eco=None, name=None):
    return SimpleNamespace(
        id=game_id,
        user_color=color,
        result=result,
        opening_code=eco,
        opening_name=name,
        pgn=None,
    )


def test_empty_opening_profile_is_null_safe():
    result = build_player_opening_intelligence(())
    assert result.selected_games == 0
    assert result.recognition_coverage_rate is None
    assert result.top == ()
    assert result.by_color == {Color.WHITE: (), Color.BLACK: ()}


def test_openings_group_by_identity_with_user_perspective_results():
    games = (
        game(1, result="win", eco="B90", name="Sicilian Defense: Najdorf Variation, English Attack"),
        game(2, result="loss", eco="B90", name="Sicilian Defense: Najdorf Variation, English Attack"),
        game(3, result="draw", eco="C50", name="Italian Game"),
    )
    result = build_player_opening_intelligence(games)
    najdorf = result.top[0]
    assert (najdorf.games, najdorf.wins, najdorf.draws, najdorf.losses) == (2, 1, 0, 1)
    assert najdorf.family == "Sicilian Defense"
    assert najdorf.variation == "Najdorf Variation"
    assert najdorf.subvariation == "English Attack"
    assert result.recognition_coverage_rate == 1.0


def test_eco_only_is_grouped_without_inventing_name_or_variation():
    result = build_player_opening_intelligence((game(1, eco="B13"), game(2, eco="B13")))
    record = result.top[0]
    assert record.eco == "B13" and record.games == 2
    assert record.name is None and record.family is None and record.variation is None
    assert result.games_with_recognized_opening == 0
    assert result.games_with_opening_identity == 2


def test_color_split_and_stable_ordering():
    games = (
        game(1, color="black", eco="B20", name="Sicilian Defense"),
        game(2, color="black", eco="B20", name="Sicilian Defense"),
        game(3, color="white", eco="C50", name="Italian Game"),
        game(4, color="invalid", eco="A00", name="Amar Opening"),
    )
    result = build_player_opening_intelligence(games)
    assert result.by_color[Color.BLACK][0].games == 2
    assert result.by_color[Color.WHITE][0].name == "Italian Game"
    assert all(item.name != "Amar Opening" for rows in result.by_color.values() for item in rows)
    assert [item.games for item in result.top] == [2, 1, 1]
