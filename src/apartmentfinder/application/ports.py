"""Application-layer protocols used to keep infrastructure replaceable."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from apartmentfinder.domain.models import Listing, SearchRequest


class ListingSource(Protocol):
    """A parser source that can search and enrich real-estate listings."""

    code: str

    def search_pages(
        self,
        request: SearchRequest,
        max_pages: int,
        delay_seconds: float,
    ) -> Iterable[Listing]:
        """Yield listings matching one normalized request."""

    def fetch_listing_detail(self, listing: Listing) -> Listing:
        """Return an enriched listing before notification."""

    def close(self) -> None:
        """Close source resources."""


class ListingRepository(Protocol):
    """Persistence operations needed by monitoring use cases."""


class NotificationSender(Protocol):
    """Message sender abstraction for future non-Telegram interfaces."""
