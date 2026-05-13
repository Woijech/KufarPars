import pytest

from kufarpars.client import KufarNetworkError, SearchRequest
from kufarpars.listing_sources import SourceNetworkError, fetch_from_sources
from kufarpars.models import Listing


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


def test_fetch_from_sources_combines_kufar_and_realt(monkeypatch) -> None:
    monkeypatch.setattr(
        "kufarpars.listing_sources.KufarSource",
        lambda: FakeSource(
            "kufar",
            [Listing(ad_id=1, title="Kufar", url="https://k.test/1")],
        ),
    )
    monkeypatch.setattr(
        "kufarpars.listing_sources.RealtSource",
        lambda: FakeSource(
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
    )

    listings = fetch_from_sources(SearchRequest())

    assert [(listing.source, listing.ad_id) for listing in listings] == [
        ("kufar", 1),
        ("realt", 1),
    ]


def test_fetch_from_sources_keeps_working_when_one_source_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        "kufarpars.listing_sources.KufarSource",
        lambda: FakeSource("kufar", error=KufarNetworkError("blocked")),
    )
    monkeypatch.setattr(
        "kufarpars.listing_sources.RealtSource",
        lambda: FakeSource(
            "realt",
            [Listing(ad_id=2, title="Realt", url="https://r.test/2", source="realt")],
        ),
    )

    listings = fetch_from_sources(SearchRequest())

    assert [listing.source for listing in listings] == ["realt"]


def test_fetch_from_sources_raises_when_all_sources_fail(monkeypatch) -> None:
    monkeypatch.setattr(
        "kufarpars.listing_sources.KufarSource",
        lambda: FakeSource("kufar", error=KufarNetworkError("blocked")),
    )
    monkeypatch.setattr(
        "kufarpars.listing_sources.RealtSource",
        lambda: FakeSource("realt", error=KufarNetworkError("blocked")),
    )

    with pytest.raises(SourceNetworkError):
        fetch_from_sources(SearchRequest())
