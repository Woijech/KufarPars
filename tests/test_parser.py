import json

from kufarpars.parser import parse_search_page


def test_parse_search_page_extracts_listings() -> None:
    payload = {
        "props": {
            "initialState": {
                "listing": {
                    "ads": [
                        {
                            "ad_id": 123,
                            "ad_link": "https://re.kufar.by/vi/123?rank=1",
                            "ad_parameters": [
                                {"p": "rooms", "vl": "2"},
                                {"p": "size", "v": 48.5},
                                {"p": "floor", "vl": ["5"]},
                                {"p": "re_number_floors", "vl": ["9"]},
                                {"p": "metro", "vl": ["Грушевка"]},
                            ],
                            "account_parameters": [
                                {"p": "name", "v": "Анна"},
                                {"p": "address", "v": "Минск"},
                            ],
                            "body_short": "Уютная квартира.",
                            "company_ad": False,
                            "currency": "USD",
                            "list_time": "2026-05-07T09:30:55Z",
                            "price_byn": "141300",
                            "price_usd": "50000",
                            "subject": "Квартира",
                        }
                    ],
                    "pagination": [{"label": "next", "token": "cursor-2"}],
                    "searchId": "search-id",
                    "total": "42",
                }
            }
        }
    }
    html = (
        '<script id="__NEXT_DATA__" type="application/json">'
        f"{json.dumps(payload)}"
        "</script>"
    )

    result = parse_search_page(html)

    assert result.total == 42
    assert result.next_cursor == "cursor-2"
    assert result.search_id == "search-id"
    assert len(result.listings) == 1
    assert result.listings[0].price_usd == 500
    assert result.listings[0].url == "https://re.kufar.by/vi/123"
    assert result.listings[0].metro == ["Грушевка"]
