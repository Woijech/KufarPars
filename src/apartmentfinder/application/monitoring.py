"""Reusable monitoring helpers independent from Telegram and site parsers."""

from __future__ import annotations

from apartmentfinder.domain.models import Listing, ListingKey


def listings_after_watch_start(profile, listings: list[Listing]) -> list[Listing]:
    """Return listings eligible after monitoring was enabled."""
    if profile.watch_started_at is None:
        return []
    return [
        listing
        for listing in listings
        if listing.published_at is None
        or listing.published_at > profile.watch_started_at
    ]


def listing_key(listing: Listing) -> ListingKey:
    """Return the storage identity for a listing."""
    return (listing.source, listing.ad_id)
