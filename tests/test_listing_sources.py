import pytest

from apartmentfinder.application.source_registry import (
    SourceNetworkError,
    fetch_from_sources,
)
from apartmentfinder.domain.models import Listing, SearchRequest
from apartmentfinder.infrastructure.source_registry import configured_sources


class FakeSource:
    """Small source double used to test aggregation without network."""

    def __init__(self, code, listings=None, error=None):
        self.code = code
        self._listings = listings or []
        self._error = error

    def search_pages(self, request, max_pages, delay_seconds):
        if self._error:
            raise self._error
        return self._listings

    def close(self):
        pass


def test_fetch_from_sources_combines_multiple_sources() -> None:
    sources = [
        FakeSource(
            "kufar",
            [Listing(ad_id=1, title="Kufar", url="https://k.test/1")],
        ),
        FakeSource(
            "realt",
            [
                Listing(
                    ad_id=1,
                    title="Realt",
                    url="https://r.test/1",
                    source="realt",
                )
            ],
        ),
    ]

    listings = fetch_from_sources(
        SearchRequest(),
        sources,
        max_pages=1,
        delay_seconds=0,
    )

    assert [(listing.source, listing.ad_id) for listing in listings] == [
        ("kufar", 1),
        ("realt", 1),
    ]


def test_fetch_from_sources_keeps_working_when_one_source_fails() -> None:
    sources = [
        FakeSource("kufar", error=RuntimeError("blocked")),
        FakeSource(
            "realt",
            [Listing(ad_id=2, title="Realt", url="https://r.test/2", source="realt")],
        ),
    ]

    listings = fetch_from_sources(
        SearchRequest(),
        sources,
        max_pages=1,
        delay_seconds=0,
    )

    assert [listing.source for listing in listings] == ["realt"]


def test_fetch_from_sources_raises_when_all_sources_fail() -> None:
    sources = [
        FakeSource("kufar", error=RuntimeError("blocked")),
        FakeSource("realt", error=RuntimeError("blocked")),
    ]

    with pytest.raises(SourceNetworkError):
        fetch_from_sources(
            SearchRequest(),
            sources,
            max_pages=1,
            delay_seconds=0,
        )


def test_configured_sources_returns_kufar_and_realt_sources() -> None:
    sources = configured_sources()

    try:
        assert [source.code for source in sources] == ["kufar", "realt"]
    finally:
        for source in sources:
            source.close()
