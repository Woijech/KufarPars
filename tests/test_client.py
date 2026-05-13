import httpx
import pytest

from apartmentfinder.domain.models import SearchRequest
from apartmentfinder.infrastructure.sources.kufar.client import (
    KufarClient,
    KufarNetworkError,
    kufar_params,
    kufar_path,
)


def test_search_request_builds_rent_url_parts() -> None:
    request = SearchRequest(rooms=2, max_price=500, text="возле метро")

    assert kufar_path(request) == "/l/minsk/snyat/kvartiru/2k"
    assert kufar_params(request)["prc"] == "r:0,500"
    assert kufar_params(request)["query"] == "возле метро"


def test_search_request_builds_room_url_parts() -> None:
    request = SearchRequest(property_type="room", rooms=2)

    assert kufar_path(request) == "/l/minsk/snyat/komnatu"


def test_search_request_keeps_local_only_filters_out_of_kufar_params() -> None:
    request = SearchRequest(
        district="Центральный",
        metro="Немига",
        include_keywords=["без хозяев"],
        exclude_keywords=["койко-место"],
    )

    params = kufar_params(request)

    assert "district" not in params
    assert "metro" not in params
    assert "include_keywords" not in params
    assert "exclude_keywords" not in params


def test_client_wraps_forbidden_status_as_network_error() -> None:
    client = KufarClient(retries=0)
    client._client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(403, request=request)
        )
    )

    with pytest.raises(KufarNetworkError):
        client.fetch_url("https://example.test/status/403")


def test_client_accepts_explicit_proxy_url() -> None:
    client = KufarClient(proxy_url="http://127.0.0.1:8080")

    assert client._proxy_url == "http://127.0.0.1:8080"
