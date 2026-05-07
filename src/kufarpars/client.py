from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from time import sleep
from urllib.parse import urlencode

import httpx

from kufarpars.config import settings
from kufarpars.models import Listing
from kufarpars.parser import parse_search_page

ROOM_PATHS = {1: "1k", 2: "2k", 3: "3k", 4: "4k"}
DEAL_PATHS = {"rent": "snyat", "buy": "kupit"}
PROPERTY_PATHS = {"apartment": "kvartiru", "room": "komnatu"}
SORT_VALUES = {"newest": None, "cheap": "prc.a", "expensive": "prc.d"}


@dataclass(frozen=True)
class SearchRequest:
    city: str = "minsk"
    deal: str = "rent"
    property_type: str = "apartment"
    rooms: int | None = None
    min_price: int | None = None
    max_price: int | None = None
    currency: str = "USD"
    text: str | None = None
    sort: str = "newest"
    size: int = 30
    extra_params: dict[str, str] = field(default_factory=dict)

    def path(self) -> str:
        deal_path = DEAL_PATHS[self.deal]
        property_path = PROPERTY_PATHS[self.property_type]
        parts = ["l", self.city, deal_path, property_path]
        if self.property_type == "apartment" and self.rooms in ROOM_PATHS:
            parts.append(ROOM_PATHS[self.rooms])
        return "/" + "/".join(parts)

    def params(self) -> dict[str, str]:
        params = {
            "cur": self.currency,
            "size": str(self.size),
        }
        if self.text:
            params["query"] = self.text
        if self.min_price is not None or self.max_price is not None:
            lower = self.min_price if self.min_price is not None else 0
            upper = self.max_price if self.max_price is not None else 1_000_000_000
            params["prc"] = f"r:{lower},{upper}"
        sort_value = SORT_VALUES[self.sort]
        if sort_value:
            params["sort"] = sort_value
        params.update(self.extra_params)
        return params


class KufarClient:
    def __init__(
        self,
        base_url: str = settings.realty_url,
        timeout_seconds: float = settings.timeout_seconds,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "ru,en;q=0.8",
                "User-Agent": settings.user_agent,
            },
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> KufarClient:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def search_pages(
        self,
        request: SearchRequest,
        max_pages: int = 1,
        delay_seconds: float = 1.0,
    ) -> Iterable[Listing]:
        params = request.params()
        cursor: str | None = None

        for page_number in range(max_pages):
            page_params = params | ({"cursor": cursor} if cursor else {})
            result = self.search_page(request.path(), page_params)
            yield from result.listings

            cursor = result.next_cursor
            if not cursor:
                break
            if page_number < max_pages - 1 and delay_seconds > 0:
                sleep(delay_seconds)

    def search_page(self, path: str, params: dict[str, str]):
        return parse_search_page(self.fetch_html(path, params))

    def fetch_html(self, path: str, params: dict[str, str]) -> str:
        url = self._url(path, params)
        response = self._client.get(url)
        response.raise_for_status()
        return response.text

    def _url(self, path: str, params: dict[str, str]) -> str:
        query = urlencode(params)
        return f"{self._base_url}{path}?{query}"
