from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kufarpars.parser import extract_next_data


@dataclass(frozen=True)
class FilterOption:
    value: str
    label: str


@dataclass(frozen=True)
class KufarFilter:
    code: str
    name: str
    value_type: str
    multi: bool
    options: list[FilterOption] = field(default_factory=list)
    range_hint: dict[str, Any] | None = None


def parse_filter_catalog(html: str) -> list[KufarFilter]:
    data = extract_next_data(html)
    filters = data["props"]["initialState"]["filters"].get("currentFilters") or []
    catalog: list[KufarFilter] = []
    seen_codes: set[str] = set()

    for item in filters:
        code = item.get("url_name")
        if not code or code in seen_codes:
            continue
        seen_codes.add(code)
        catalog.append(
            KufarFilter(
                code=code,
                name=_label(item),
                value_type=item.get("type") or "",
                multi=bool(item.get("multi")),
                options=_options(item.get("values")),
                range_hint=item.get("range"),
            )
        )
    return catalog


def find_filter(catalog: list[KufarFilter], code: str) -> KufarFilter | None:
    for item in catalog:
        if item.code == code:
            return item
    return None


def _label(item: dict[str, Any]) -> str:
    labels = item.get("labels") or {}
    name = labels.get("name") or {}
    return name.get("ru") or item.get("name") or item.get("url_name") or ""


def _options(values: Any) -> list[FilterOption]:
    if not isinstance(values, list):
        return []
    result = []
    for value in values:
        labels = value.get("labels") or {}
        result.append(
            FilterOption(
                value=str(value.get("value")),
                label=labels.get("ru") or str(value.get("value")),
            )
        )
    return result
