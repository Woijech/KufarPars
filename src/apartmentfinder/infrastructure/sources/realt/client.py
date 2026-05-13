"""HTTP client for Realt.by rental listings."""

from __future__ import annotations

from collections.abc import Iterable
from time import sleep

import httpx

from apartmentfinder.domain.models import Listing, SearchRequest
from apartmentfinder.infrastructure.config import settings
from apartmentfinder.infrastructure.sources.realt.parser import (
    parse_realt_detail_page,
    parse_realt_search_page,
)

REALT_BASE_URL = "https://realt.by"
REALT_PATHS = {
    "apartment": "/rent/flat-for-long/",
    "room": "/rent/room-for-long/",
}


class RealtNetworkError(RuntimeError):
    """Raised when Realt cannot be reached after retry attempts."""


class RealtClient:
    """Synchronous Realt.by client used by background bot jobs."""

    def __init__(
        self,
        base_url: str = REALT_BASE_URL,
        timeout_seconds: float = settings.timeout_seconds,
        retries: int = settings.request_retries,
        retry_delay_seconds: float = settings.request_retry_delay_seconds,
        proxy_url: str | None = settings.http_proxy,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._retries = max(retries, 0)
        self._retry_delay_seconds = max(retry_delay_seconds, 0)
        self._proxy_url = proxy_url
        self._client = httpx.Client(
            proxy=proxy_url,
            timeout=httpx.Timeout(
                timeout_seconds,
                connect=timeout_seconds,
                read=timeout_seconds,
            ),
            follow_redirects=True,
            headers={
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "ru,en;q=0.8",
                "User-Agent": settings.user_agent,
            },
        )

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()

    def __enter__(self) -> RealtClient:
        """Enter a context-managed client session."""
        return self

    def __exit__(self, *_args: object) -> None:
        """Close the client session when leaving a context manager."""
        self.close()

    def search_pages(
        self,
        request: SearchRequest,
        max_pages: int = 1,
        delay_seconds: float = 1.0,
    ) -> Iterable[Listing]:
        """Yield listings from one or more Realt search pages."""
        path = REALT_PATHS.get(request.property_type)
        if path is None:
            return
        next_url: str | None = self._url(path, {})
        for page_number in range(max_pages):
            if next_url is None:
                break
            result = parse_realt_search_page(
                self.fetch_url(next_url),
                base_url=self._base_url,
                property_type=request.property_type,
            )
            yield from result.listings
            next_url = result.next_cursor
            if page_number < max_pages - 1 and delay_seconds > 0:
                sleep(delay_seconds)

    def fetch_listing_detail(self, listing: Listing) -> Listing:
        """Fetch a listing detail page to get richer text and gallery URLs."""
        return parse_realt_detail_page(
            self.fetch_url(listing.url),
            listing,
            base_url=self._base_url,
        )

    def fetch_url(self, url: str) -> str:
        """Fetch an absolute or site-relative URL and return response text."""
        if url.startswith("/"):
            url = f"{self._base_url}{url}"
        last_error: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                response = self._client.get(url)
                response.raise_for_status()
                return response.text
            except (
                httpx.TimeoutException,
                httpx.NetworkError,
                httpx.HTTPStatusError,
            ) as error:
                last_error = error
                if attempt < self._retries:
                    sleep(self._retry_delay_seconds)
                    continue
                break
        raise RealtNetworkError(f"Realt request failed: {url}") from last_error

    def _url(self, path: str, _params: dict[str, str]) -> str:
        """Build an absolute URL for a Realt path."""
        return f"{self._base_url}{path}"
