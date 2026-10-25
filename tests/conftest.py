import os
from pathlib import Path

import pytest
from hypothesis import settings

from scamcheck.data.io import load_items

# Failing examples print a reproduction blob. In CI (HYPOTHESIS_PROFILE=ci) the search is derandomized, so a
# failure reproduces on every run; locally the example database replays the last failure first.
settings.register_profile("default", print_blob=True, deadline=None)
settings.register_profile("ci", print_blob=True, deadline=None, derandomize=True, max_examples=150)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "default"))

FIXTURES = Path(__file__).parent / "fixtures"
VALID = FIXTURES / "synthetic_items.jsonl"
INVALID = FIXTURES / "invalid_items.jsonl"


@pytest.fixture
def items():
    res = load_items(VALID)
    assert not res.errors, res.errors
    return res.items
