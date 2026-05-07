from kufarpars.cli import build_parser


def test_cli_uses_default_base_url() -> None:
    args = build_parser().parse_args([])

    assert args.base_url == "https://www.kufar.by"


def test_cli_parses_search_options() -> None:
    args = build_parser().parse_args(
        ["search", "--rooms", "2", "--max-price", "500", "--format", "json"]
    )

    assert args.command == "search"
    assert args.rooms == 2
    assert args.max_price == 500
    assert args.format == "json"
