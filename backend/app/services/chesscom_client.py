from collections.abc import Iterator
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any
from urllib.parse import quote

import httpx


class ChessComError(RuntimeError):
    pass


class ChessComUserNotFoundError(ChessComError):
    pass


class ChessComNetworkError(ChessComError):
    pass


class ChessComResponseError(ChessComError):
    pass


@dataclass(frozen=True)
class ChessComGameRecord:
    external_id: str
    url: str | None
    pgn: str | None
    end_time: int | None


class ChessComClient:
    def __init__(
        self,
        user_agent: str,
        *,
        timeout: float = 15.0,
        base_url: str = "https://api.chess.com/pub",
        http_client: httpx.Client | None = None,
    ) -> None:
        self._client = http_client or httpx.Client(timeout=timeout)
        self._base_url = base_url.rstrip("/")
        self._headers = {"User-Agent": user_agent, "Accept": "application/json"}

    def close(self) -> None:
        self._client.close()

    def _get_json(self, url: str, *, user_lookup: bool = False) -> dict[str, Any]:
        try:
            response = self._client.get(url, headers=self._headers)
        except (httpx.TimeoutException, httpx.NetworkError) as error:
            raise ChessComNetworkError("Unable to reach Chess.com") from error
        if response.status_code == 404 and user_lookup:
            raise ChessComUserNotFoundError("Chess.com user was not found")
        if response.is_error:
            raise ChessComResponseError(
                f"Chess.com returned HTTP {response.status_code}"
            )
        try:
            payload = response.json()
        except (ValueError, json.JSONDecodeError) as error:
            raise ChessComResponseError("Chess.com returned invalid JSON") from error
        if not isinstance(payload, dict):
            raise ChessComResponseError("Chess.com response must be a JSON object")
        return payload

    def get_archives(self, username: str) -> list[str]:
        encoded_username = quote(username.strip(), safe="")
        payload = self._get_json(
            f"{self._base_url}/player/{encoded_username}/games/archives",
            user_lookup=True,
        )
        archives = payload.get("archives")
        if not isinstance(archives, list) or any(not isinstance(item, str) for item in archives):
            raise ChessComResponseError("Chess.com archives must be a list of URLs")
        unique = list(dict.fromkeys(archives))

        def archive_key(url: str) -> tuple[int, int, int]:
            match = re.search(r"/games/(\d{4})/(\d{2})/?$", url)
            return (1, int(match.group(1)), int(match.group(2))) if match else (0, 0, 0)

        return sorted(unique, key=archive_key, reverse=True)

    @staticmethod
    def _external_id(record: dict[str, Any]) -> str:
        url = record.get("url")
        if isinstance(url, str) and url.strip():
            return url.strip()
        pgn = record.get("pgn")
        source = pgn if isinstance(pgn, str) and pgn else json.dumps(record, sort_keys=True, separators=(",", ":"))
        return f"sha256:{hashlib.sha256(source.encode('utf-8')).hexdigest()}"

    def get_archive_games(self, archive_url: str) -> list[ChessComGameRecord]:
        payload = self._get_json(archive_url)
        games = payload.get("games")
        if not isinstance(games, list) or any(not isinstance(item, dict) for item in games):
            raise ChessComResponseError("Chess.com games must be a list of objects")
        records = [
            ChessComGameRecord(
                external_id=self._external_id(item),
                url=item.get("url") if isinstance(item.get("url"), str) else None,
                pgn=item.get("pgn") if isinstance(item.get("pgn"), str) else None,
                end_time=int(item["end_time"]) if isinstance(item.get("end_time"), (int, float)) else None,
            )
            for item in games
        ]
        return sorted(records, key=lambda item: (item.end_time is not None, item.end_time or 0), reverse=True)

    def iter_recent_games(self, username: str) -> Iterator[ChessComGameRecord]:
        for archive_url in self.get_archives(username):
            yield from self.get_archive_games(archive_url)
