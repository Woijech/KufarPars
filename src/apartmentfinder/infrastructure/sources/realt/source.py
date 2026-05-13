"""Realt.by source adapter implementation."""

from __future__ import annotations

from collections.abc import Iterable

from apartmentfinder.domain.models import Listing, SearchRequest
from apartmentfinder.infrastructure.config import settings
from apartmentfinder.infrastructure.sources.realt.client import RealtClient


class RealtSource:
    """Listing source adapter for Realt.by."""

    code = "realt"

    def __init__(self) -> None:
        self._client = RealtClient(
            timeout_seconds=settings.bot_fetch_timeout_seconds,
            retries=settings.bot_fetch_retries,
            retry_delay_seconds=settings.bot_fetch_retry_delay_seconds,
        )

    def search_pages(
        self,
        request: SearchRequest,
        max_pages: int,
        delay_seconds: float,
    ) -> Iterable[Listing]:
        """Yield listings from Realt.by."""
        return self._client.search_pages(request, max_pages, delay_seconds)

    def fetch_listing_detail(self, listing: Listing) -> Listing:
        """Fetch full Realt listing details."""
        return self._client.fetch_listing_detail(listing)

    def close(self) -> None:
        """Close HTTP connections."""
        self._client.close()
