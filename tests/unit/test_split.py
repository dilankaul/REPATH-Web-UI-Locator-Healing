from repath_evaluation.data.split import load_site_split


def test_grouped_split_defaults_to_test_and_expands_all(tmp_path) -> None:
    path = tmp_path / "split.yaml"
    path.write_text(
        "default_group: test\n"
        "development_sites:\n  - dev-a\n  - dev-b\n"
        "test_sites:\n  - test-a\n",
        encoding="utf-8",
    )

    split = load_site_split(path)

    assert split.sites == ("test-a",)
    assert split.group("development") == ("dev-a", "dev-b")
    assert split.group("test") == ("test-a",)
    assert split.group("all") == ("dev-a", "dev-b", "test-a")


def test_repository_split_contains_the_configured_16_development_and_6_test_sites() -> None:
    from pathlib import Path

    split = load_site_split(Path("configs/site_split.yaml"))

    assert len(split.development_sites) == 16
    assert len(split.test_sites) == 6
    assert split.default_group == "test"
    assert split.test_sites == (
        "book-2016-2019",
        "beijing-2017-2019",
        "instagram",
        "movie-2014-2019",
        "xfinity-2018-2020",
        "yahoo",
    )
