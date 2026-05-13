"""Concrete source registry for the production ApartmentFinder app."""

from __future__ import annotations

from apartmentfinder.application.ports import ListingSource
from apartmentfinder.infrastructure.sources.kufar.source import KufarSource
from apartmentfinder.infrastructure.sources.realt.source import RealtSource


def configured_sources() -> list[ListingSource]:
    """Create all listing sources enabled for the application."""
    return [KufarSource(), RealtSource()]


def configured_source_map() -> dict[str, ListingSource]:
    """Create a source lookup by source code for detail enrichment."""
    return {source.code: source for source in configured_sources()}
