"""Source-neutral listing filtering rules."""

from __future__ import annotations

from apartmentfinder.domain.models import Listing, SearchRequest


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
            return False
    if not listing_matches_price(listing, request):
        return False
    if request.metro and request.metro.casefold() not in haystack:
        return False
    if request.district and request.district.casefold() not in haystack:
        return False
    if any(keyword.casefold() not in haystack for keyword in request.include_keywords):
        return False
    return not any(
        keyword.casefold() in haystack for keyword in request.exclude_keywords
    )


def listing_matches_price(listing: Listing, request: SearchRequest) -> bool:
    """Return whether a listing price fits the configured USD range."""
    if request.min_price is None and request.max_price is None:
        return True
    if listing.price_usd is None:
        return False
    if request.min_price is not None and listing.price_usd < request.min_price:
        return False
    return request.max_price is None or listing.price_usd <= request.max_price
