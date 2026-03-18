import pytest
from core.logic import correct_tests

def test_correct_tests_early_return():
    """Test that correct_tests returns early when student_responses is empty."""
    res, stats = correct_tests([], [], {}, {}, None)
    assert res == {}
    assert stats == {}
