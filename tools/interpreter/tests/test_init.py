"""Smoke tests for neminterp package."""


def test_import() -> None:
    import neminterp

    assert neminterp.__version__ == "0.1.0"
