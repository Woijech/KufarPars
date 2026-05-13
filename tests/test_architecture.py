import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_application_and_domain_do_not_import_source_adapters() -> None:
    source_specific_fragments = [
        "infrastructure.sources.kufar",
        "infrastructure.sources.realt",
        "KufarSource",
        "RealtSource",
    ]

    for path in [
        *PROJECT_ROOT.joinpath("src/apartmentfinder/domain").rglob("*.py"),
        *PROJECT_ROOT.joinpath("src/apartmentfinder/application").rglob("*.py"),
    ]:
        text = path.read_text(encoding="utf-8")
        assert not any(fragment in text for fragment in source_specific_fragments), path


def test_pyproject_exposes_only_apartmentfinder_bot_entrypoint() -> None:
    data = tomllib.loads(PROJECT_ROOT.joinpath("pyproject.toml").read_text())
    scripts = data["project"]["scripts"]

    assert scripts["apartmentfinder-bot"] == (
        "apartmentfinder.interfaces.telegram.bot:main"
    )
