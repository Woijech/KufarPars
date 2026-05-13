"""Source orchestration helpers that depend only on source protocols."""

from __future__ import annotations

import logging

from apartmentfinder.application.ports import ListingSource
from apartmentfinder.domain.models import Listing, SearchRequest

logger = logging.getLogger(__name__)


class SourceNetworkError(RuntimeError):
    """Raised when every configured listing source fails."""


def source_label(source: str) -> str:
    """Return a human label for one source code."""
    return {"kufar": "Kufar", "realt": "Realt"}.get(source, source)


def fetch_from_sources(
    request: SearchRequest,
    sources: list[ListingSource],
    *,
    max_pages: int,
    delay_seconds: float,
) -> list[Listing]:
    """Fetch search listings from all configured sources."""
    listings: list[Listing] = []
    failures = []
    for source in sources:
        try:
            listings.extend(
                source.search_pages(
                    request,
                    max_pages=max_pages,
                    delay_seconds=delay_seconds,
                )
            )
        except Exception as error:
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


def enrich_listing_details(
    listings: list[Listing],
    source_by_code: dict[str, ListingSource],
) -> list[Listing]:
    """Fetch detail pages with the source that owns each listing."""
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
