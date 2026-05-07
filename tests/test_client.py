from kufarpars.client import SearchRequest


def test_search_request_builds_rent_url_parts() -> None:
    request = SearchRequest(rooms=2, max_price=500, text="возле метро")

    assert request.path() == "/l/minsk/snyat/kvartiru/2k"
    assert request.params()["prc"] == "r:0,500"
    assert request.params()["query"] == "возле метро"


def test_search_request_builds_room_url_parts() -> None:
    request = SearchRequest(property_type="room", rooms=2)

    assert request.path() == "/l/minsk/snyat/komnatu"
