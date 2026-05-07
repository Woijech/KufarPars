from datetime import UTC, datetime

from kufarpars.bot_storage import UserProfile
from kufarpars.models import Listing
from kufarpars.telegram_bot import listings_after_watch_start


def test_listings_after_watch_start_keeps_only_newer_items() -> None:
    profile = UserProfile(
        chat_id=123,
        watch_started_at=datetime(2026, 5, 7, 12, 0, tzinfo=UTC),
    )
    old_listing = Listing(
        ad_id=1,
        title="Старое",
        url="https://example.test/1",
        published_at=datetime(2026, 5, 7, 11, 59, tzinfo=UTC),
    )
    new_listing = Listing(
        ad_id=2,
        title="Новое",
        url="https://example.test/2",
        published_at=datetime(2026, 5, 7, 12, 1, tzinfo=UTC),
    )
    undated_listing = Listing(
        ad_id=3,
        title="Без даты",
        url="https://example.test/3",
    )

    assert listings_after_watch_start(
        profile,
        [old_listing, new_listing, undated_listing],
    ) == [new_listing]
