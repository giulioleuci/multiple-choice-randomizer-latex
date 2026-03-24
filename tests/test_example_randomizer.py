import pytest
from unittest.mock import patch
import sys

# Mock sys.modules for pylatex since the example may not have pylatex installed
import sys
from unittest.mock import MagicMock
sys.modules['pylatex'] = MagicMock()
sys.modules['pylatex.base_classes'] = MagicMock()

# Instead of letting pylatex.base_classes.Environment be a MagicMock object,
# which causes a metaclass conflict if inherited from, we create a dummy class
class DummyEnvironment:
    def __init__(self, *args, **kwargs):
        pass

sys.modules['pylatex.base_classes'].Environment = DummyEnvironment

from example.randomizer import TestGeneratorAnalyzer


@pytest.fixture
def analyzer():
    with patch.object(TestGeneratorAnalyzer, '_load_config', return_value={"default_correct_score": 4}):
        return TestGeneratorAnalyzer()

def test_evaluate_randomness_empty(analyzer):
    # Test with empty variants
    analyzer.original_questions_order = ["Q1", "Q2"]
    metrics = analyzer.evaluate_randomness_of_variants([])
    assert metrics == {"question_order_randomness": 0, "answer_order_randomness": 0, "combined_randomness": 0}

    # Test with empty original_questions_order
    analyzer.original_questions_order = []
    variants = [{"variant_id": "1", "questions": []}]
    metrics = analyzer.evaluate_randomness_of_variants(variants)
    assert metrics == {"question_order_randomness": 0, "answer_order_randomness": 0, "combined_randomness": 0}

def test_evaluate_randomness_zero(analyzer):
    analyzer.original_questions_order = ["Q1", "Q2"]

    # Answers don't change position (correct answer is at index 0 for both variants)
    variants = [
        {
            "variant_id": "1",
            "questions": [
                {"question_text": "Q1", "answers": [{"text": "A", "is_correct": True}, {"text": "B", "is_correct": False}]},
                {"question_text": "Q2", "answers": [{"text": "C", "is_correct": True}, {"text": "D", "is_correct": False}]}
            ]
        },
        {
            "variant_id": "2",
            "questions": [
                {"question_text": "Q1", "answers": [{"text": "A", "is_correct": True}, {"text": "B", "is_correct": False}]},
                {"question_text": "Q2", "answers": [{"text": "C", "is_correct": True}, {"text": "D", "is_correct": False}]}
            ]
        }
    ]

    metrics = analyzer.evaluate_randomness_of_variants(variants)
    # Question order diff = 0, Answer order diff = 0
    assert metrics["question_order_randomness"] == 0.0
    assert metrics["answer_order_randomness"] == 0.0
    assert metrics["combined_randomness"] == 0.0

def test_evaluate_randomness_partial(analyzer):
    analyzer.original_questions_order = ["Q1", "Q2"]

    # Question order differs from original in one variant, answer positions differ
    variants = [
        {
            "variant_id": "1",
            "questions": [
                # Original order: Q1 then Q2
                {"question_text": "Q1", "answers": [{"text": "A", "is_correct": True}, {"text": "B", "is_correct": False}]},
                {"question_text": "Q2", "answers": [{"text": "C", "is_correct": True}, {"text": "D", "is_correct": False}]}
            ]
        },
        {
            "variant_id": "2",
            "questions": [
                # Reversed order: Q2 then Q1. Q1 answer changed position (index 1 is correct)
                {"question_text": "Q2", "answers": [{"text": "C", "is_correct": True}, {"text": "D", "is_correct": False}]},
                {"question_text": "Q1", "answers": [{"text": "B", "is_correct": False}, {"text": "A", "is_correct": True}]}
            ]
        }
    ]

    metrics = analyzer.evaluate_randomness_of_variants(variants)

    # For Variant 1: Q1, Q2 matches original order -> 0 diff
    # For Variant 2: Q2, Q1 differs completely from Q1, Q2 -> 2 diffs / 2 questions = 1.0
    # Mean question order randomness = (0 + 1) / 2 = 0.5
    assert metrics["question_order_randomness"] == 0.5

    # Answer positions:
    # Q1 correct answers: Variant 1 -> index 0, Variant 2 -> index 1
    # Q2 correct answers: Variant 1 -> index 0, Variant 2 -> index 0

    # std(Q1 answers) = std([0, 1]) = 0.5
    # norm_std(Q1) = 0.5 / (2 alternatives - 1) = 0.5

    # std(Q2 answers) = std([0, 0]) = 0.0
    # norm_std(Q2) = 0.0

    # Mean answer order randomness = (0.5 + 0.0) / 2 = 0.25
    assert metrics["answer_order_randomness"] == 0.25

    # Combined = (0.5 + 0.25) / 2 = 0.38 (rounded to 2)
    assert metrics["combined_randomness"] == 0.38
