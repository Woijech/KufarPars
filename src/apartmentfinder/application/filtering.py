"""Source-neutral listing filtering rules."""

from __future__ import annotations

import logging

from apartmentfinder.domain.models import Listing, SearchRequest

logger = logging.getLogger(__name__)


def listing_matches_search_filters(listing: Listing, request: SearchRequest) -> bool:
    """Apply filters that are not always represented in source URL params."""
    haystack = " ".join(
        part
        for part in [
            listing.title,
            listing.description,
            listing.address,
            " ".join(listing.metro),
        ]
        if part
    ).casefold()
    if request.rooms is not None and listing.rooms:
        if str(request.rooms) != str(listing.rooms):
            log_listing_rejected(
                listing,
                "rooms",
                "wanted=%s actual=%s",
                request.rooms,
                listing.rooms,
            )
            return False
    if not listing_matches_price(listing, request):
        return False
    if request.metro and request.metro.casefold() not in haystack:
        log_listing_rejected(listing, "metro", "wanted=%s", request.metro)
        return False
    if request.district and request.district.casefold() not in haystack:
        log_listing_rejected(listing, "district", "wanted=%s", request.district)
        return False
    for keyword in request.include_keywords:
        if keyword.casefold() not in haystack:
            log_listing_rejected(listing, "include_keyword", "missing=%s", keyword)
            return False
    for keyword in request.exclude_keywords:
        if keyword.casefold() in haystack:
            log_listing_rejected(listing, "exclude_keyword", "matched=%s", keyword)
            return False
    return True


def listing_matches_price(listing: Listing, request: SearchRequest) -> bool:
    """Return whether a listing price fits the configured USD range."""
    if request.min_price is None and request.max_price is None:
        return True
    if listing.price_usd is None:
        log_listing_rejected(listing, "price", "price_usd_missing=true")
        return False
    if request.min_price is not None and listing.price_usd < request.min_price:
        log_listing_rejected(
            listing,
            "price",
            "price_usd=%s min_price=%s",
            listing.price_usd,
            request.min_price,
        )
        return False
    if request.max_price is not None and listing.price_usd > request.max_price:
        log_listing_rejected(
            listing,
            "price",
            "price_usd=%s max_price=%s",
            listing.price_usd,
            request.max_price,
        )
        return False
    return True


def log_listing_rejected(
    listing: Listing,
    reason: str,
    detail: str,
    *args: object,
) -> None:
    """Log why one listing was filtered out without dumping long text fields."""
    logger.debug(
        "listing_filtered_out source=%s ad_id=%s reason=%s " + detail,
        listing.source,
        listing.ad_id,
        reason,
        *args,
    )
