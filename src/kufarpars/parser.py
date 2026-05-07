from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

from kufarpars.models import Listing, SearchResult


class KufarParseError(ValueError):
    """Raised when Kufar markup does not contain expected listing data."""


def parse_search_page(html: str) -> SearchResult:
    data = extract_next_data(html)
    listing_state = data["props"]["initialState"]["listing"]
    ads = listing_state.get("ads") or []

    return SearchResult(
        listings=[parse_listing(ad) for ad in ads],
        total=_parse_int(listing_state.get("total")),
        next_cursor=_next_cursor(listing_state.get("pagination") or []),
        search_id=listing_state.get("searchId"),
    )


def extract_next_data(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if script is None or not script.string:
        raise KufarParseError("Could not find __NEXT_DATA__ in Kufar page.")
    return json.loads(script.string)


def parse_listing(ad: dict[str, Any]) -> Listing:
    parameters = _parameters_by_name(ad.get("ad_parameters") or [])
    account_parameters = _parameters_by_name(ad.get("account_parameters") or [])

    return Listing(
        ad_id=int(ad["ad_id"]),
        title=ad.get("subject") or "",
        url=_clean_url(ad.get("ad_link") or ""),
        price_byn=_price_from_cents(ad.get("price_byn")),
        price_usd=_price_from_cents(ad.get("price_usd")),
        currency=ad.get("currency"),
        address=_string_or_none(account_parameters.get("address")),
        rooms=_string_or_none(parameters.get("rooms")),
        area_m2=_float_or_none(parameters.get("size")),
        floor=_first_string(parameters.get("floor")),
        total_floors=_first_string(parameters.get("re_number_floors")),
        metro=_string_list(parameters.get("metro")),
        description=ad.get("body_short") or ad.get("body"),
        published_at=_datetime_or_none(ad.get("list_time")),
        seller_name=_string_or_none(account_parameters.get("name")),
        company_ad=bool(ad.get("company_ad")),
        raw_parameters=parameters,
    )


def _parameters_by_name(parameters: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for parameter in parameters:
        name = parameter.get("p")
        if not name:
            continue
        result[name] = parameter.get("vl") or parameter.get("v")
    return result


def _next_cursor(pagination: list[dict[str, Any]]) -> str | None:
    for page in pagination:
        if page.get("label") == "next":
            return page.get("token")
    return None


def _clean_url(url: str) -> str:
    return url.split("?", maxsplit=1)[0]


def _price_from_cents(value: Any) -> float | None:
    parsed = _parse_int(value)
    if parsed is None:
        return None
    return parsed / 100


def _parse_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(str(value).replace(" ", ""))
    except ValueError:
        return None


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _datetime_or_none(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _first_string(value: Any) -> str | None:
    if isinstance(value, list):
        return str(value[0]) if value else None
    return _string_or_none(value)


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _string_or_none(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)
