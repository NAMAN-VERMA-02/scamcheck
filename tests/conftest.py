from pathlib import Path

import pytest

from scamcheck.data.io import load_items

FIXTURES = Path(__file__).parent / "fixtures"
VALID = FIXTURES / "synthetic_items.jsonl"
INVALID = FIXTURES / "invalid_items.jsonl"


@pytest.fixture
def items():
    res = load_items(VALID)
    assert not res.errors, res.errors
    return res.items
