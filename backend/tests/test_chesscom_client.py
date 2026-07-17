import httpx
import pytest

from app.services.chesscom_client import (
    ChessComClient,
    ChessComNetworkError,
    ChessComResponseError,
    ChessComUserNotFoundError,
)


def make_client(handler) -> ChessComClient:
    return ChessComClient("TestAgent/1.0", http_client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_headers_encoding_archive_order_dedup_and_game_order() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/archives"):
            return httpx.Response(200, json={"archives": [
                "https://api.chess.com/pub/player/a/games/2025/12",
                "https://api.chess.com/pub/player/a/games/2026/02",
                "https://api.chess.com/pub/player/a/games/2026/02",
            ]})
        return httpx.Response(200, json={"games": [
            {"url": "game-old", "pgn": "old", "end_time": 1},
            {"url": "game-new", "pgn": "new", "end_time": 2},
            {"url": "missing-pgn", "end_time": 3},
        ]})

    client = make_client(handler)
    archives = client.get_archives("Name With Space")
    games = client.get_archive_games(archives[0])

    assert "%20" in requests[0].url.raw_path.decode()
    assert archives == [
        "https://api.chess.com/pub/player/a/games/2026/02",
        "https://api.chess.com/pub/player/a/games/2025/12",
    ]
    assert [game.external_id for game in games] == ["missing-pgn", "game-new", "game-old"]
    assert games[0].pgn is None
    assert all(request.headers["User-Agent"] == "TestAgent/1.0" for request in requests)
    client.close()


def test_external_id_url_and_deterministic_fallback() -> None:
    assert ChessComClient._external_id({"url": " https://game/1 ", "pgn": "x"}) == "https://game/1"
    first = ChessComClient._external_id({"pgn": "same PGN"})
    second = ChessComClient._external_id({"pgn": "same PGN"})
    assert first == second
    assert first.startswith("sha256:")


@pytest.mark.parametrize(
    ("response", "method", "exception"),
    [
        (httpx.Response(404, json={}), "archives", ChessComUserNotFoundError),
        (httpx.Response(500, json={}), "archives", ChessComResponseError),
        (httpx.Response(200, content=b"not-json"), "archives", ChessComResponseError),
        (httpx.Response(200, json={}), "archives", ChessComResponseError),
        (httpx.Response(200, json={"archives": "wrong"}), "archives", ChessComResponseError),
        (httpx.Response(200, json={}), "games", ChessComResponseError),
        (httpx.Response(200, json={"games": "wrong"}), "games", ChessComResponseError),
    ],
)
def test_http_and_structure_errors(response, method: str, exception: type[Exception]) -> None:
    client = make_client(lambda request: response)
    with pytest.raises(exception):
        client.get_archives("name") if method == "archives" else client.get_archive_games("https://archive")
    client.close()


@pytest.mark.parametrize("error_type", [httpx.ReadTimeout, httpx.ConnectError])
def test_network_errors_are_normalized(error_type) -> None:
    def handler(request: httpx.Request):
        raise error_type("network failed", request=request)

    client = make_client(handler)
    with pytest.raises(ChessComNetworkError):
        client.get_archives("name")
    client.close()


def test_lazy_iteration_does_not_request_old_archive_until_needed() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path.endswith("archives"):
            return httpx.Response(200, json={"archives": ["https://host/games/2026/02", "https://host/games/2026/01"]})
        return httpx.Response(200, json={"games": [{"url": request.url.path, "pgn": "pgn", "end_time": 1}]})

    client = make_client(handler)
    iterator = client.iter_recent_games("name")
    next(iterator)
    assert "/games/2026/01" not in paths
    client.close()
