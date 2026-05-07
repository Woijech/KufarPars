from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Listing:
    ad_id: int
    title: str
    url: str
    price_byn: float | None = None
    price_usd: float | None = None
    currency: str | None = None
    address: str | None = None
    rooms: str | None = None
    area_m2: float | None = None
    floor: str | None = None
    total_floors: str | None = None
    metro: list[str] = field(default_factory=list)
    description: str | None = None
    published_at: datetime | None = None
    seller_name: str | None = None
    company_ad: bool = False
    raw_parameters: dict[str, Any] = field(default_factory=dict)

    @property
    def price_label(self) -> str:
        if self.price_usd is not None:
            return f"{self.price_usd:g} $"
        if self.price_byn is not None:
            return f"{self.price_byn:g} BYN"
        return "Договорная"

    @property
    def short_location(self) -> str:
        parts = [self.address, ", ".join(self.metro)]
        return " | ".join(part for part in parts if part)


@dataclass(frozen=True)
class SearchResult:
    listings: list[Listing]
    total: int | None
    next_cursor: str | None
    search_id: str | None
