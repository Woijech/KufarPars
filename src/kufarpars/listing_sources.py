"""Source adapters that let the bot poll multiple real-estate sites."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Protocol

from kufarpars.client import KufarClient, KufarNetworkError, SearchRequest
from kufarpars.config import settings
from kufarpars.models import Listing
from kufarpars.realt_client import RealtClient, RealtNetworkError

logger = logging.getLogger(__name__)


class ListingSource(Protocol):
    """Common interface for a search source used by the bot."""

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


class SourceNetworkError(RuntimeError):
    """Raised when every configured listing source fails."""


class KufarSource:
    """Listing source adapter for Kufar."""

    code = "kufar"

    def __init__(self) -> None:
        self._client = KufarClient(
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
        """Yield listings from Kufar."""
        return self._client.search_pages(request, max_pages, delay_seconds)

    def fetch_listing_detail(self, listing: Listing) -> Listing:
        """Fetch full Kufar listing details."""
        return self._client.fetch_listing_detail(listing)

    def close(self) -> None:
        """Close HTTP connections."""
        self._client.close()


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


def source_label(source: str) -> str:
    """Return a human label for one source code."""
    return {"kufar": "Kufar", "realt": "Realt"}.get(source, source)


def fetch_from_sources(request: SearchRequest) -> list[Listing]:
    """Fetch search listings from all configured sources."""
    sources: list[ListingSource] = [KufarSource(), RealtSource()]
    listings: list[Listing] = []
    failures = []
    for source in sources:
        try:
            listings.extend(
                source.search_pages(
                    request,
                    max_pages=settings.bot_max_pages,
                    delay_seconds=settings.bot_page_delay_seconds,
                )
            )
        except (KufarNetworkError, RealtNetworkError) as error:
            logger.warning(
                "listing_source_failed source=%s error=%s",
                source.code,
                error,
            )
            failures.append(error)
        finally:
            source.close()
    if not listings and failures:
        raise SourceNetworkError("All listing sources failed") from failures[-1]
    return listings


def enrich_listing_details(listings: list[Listing]) -> list[Listing]:
    """Fetch detail pages with the source that owns each listing."""
    source_by_code: dict[str, ListingSource] = {
        "kufar": KufarSource(),
        "realt": RealtSource(),
    }
    enriched = []
    try:
        for listing in listings:
            source = source_by_code.get(listing.source)
            if source is None:
                enriched.append(listing)
                continue
            try:
                enriched.append(source.fetch_listing_detail(listing))
            except Exception:
                logger.exception(
                    "listing_enrichment_failed source=%s ad_id=%s",
                    listing.source,
                    listing.ad_id,
                )
                enriched.append(listing)
    finally:
        for source in source_by_code.values():
            source.close()
    return enriched
