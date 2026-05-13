import json

from apartmentfinder.infrastructure.sources.kufar.filters import (
    find_filter,
    parse_filter_catalog,
)


def test_parse_filter_catalog_extracts_codes_and_options() -> None:
    payload = {
        "props": {
            "initialState": {
                "filters": {
                    "currentFilters": [
                        {
                            "url_name": "prc",
                            "labels": {"name": {"ru": "Цена"}},
                            "type": "int",
                            "multi": False,
                            "values": None,
                            "range": {"lower": 0, "upper": 1000},
                        },
                        {
                            "url_name": "mee",
                            "labels": {"name": {"ru": "Метро"}},
                            "type": "int",
                            "multi": True,
                            "values": [
                                {
                                    "value": "6",
                                    "labels": {"ru": "Грушевка"},
                                }
                            ],
                            "range": None,
                        },
                    ]
                }
            }
        }
    }
    html = (
        '<script id="__NEXT_DATA__" type="application/json">'
        f"{json.dumps(payload)}"
        "</script>"
    )

    catalog = parse_filter_catalog(html)

    assert find_filter(catalog, "prc").range_hint == {"lower": 0, "upper": 1000}
    assert find_filter(catalog, "mee").options[0].label == "Грушевка"
