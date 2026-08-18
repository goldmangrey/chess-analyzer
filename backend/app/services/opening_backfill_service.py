from app.models import Color, Game
from app.services.pgn_parser import parse_pgn


def refresh_game_opening(game: Game) -> bool:
    """Refresh opening metadata from saved PGN without engine analysis."""
    username = game.white_username if game.user_color is Color.WHITE else game.black_username
    parsed = parse_pgn(game.pgn, username, game.external_id, platform=game.platform)
    changed = (
        game.opening_code != parsed.opening_code
        or game.opening_name != parsed.opening_name
    )
    if changed:
        game.opening_code = parsed.opening_code
        game.opening_name = parsed.opening_name
    return changed
