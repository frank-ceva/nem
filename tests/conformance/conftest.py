"""Pytest configuration for conformance tests."""

import pytest
from tests.conformance.runners.interpreter_runner import InterpreterRunner


def get_available_runners():
    """Return list of available conformance runners."""
    runners = [InterpreterRunner()]
    return runners


@pytest.fixture(params=get_available_runners(), ids=lambda r: r.name)
def runner(request):
    """Provide conformance runner for testing.

    This fixture is parametrized to run tests against all available runners.
    Currently includes:
    - interpreter: Uses nemlib parser and interpreter
    """
    return request.param
