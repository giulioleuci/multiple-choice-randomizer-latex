import pytest
from unittest.mock import patch, mock_open
import numpy as np
import sys
import os

# Create mock objects for pylatex since we're testing randomizer directly
class MockDocument:
    def __init__(self, *args, **kwargs):
        self.packages = []
        self.preamble = []
    def append(self, *args, **kwargs): pass
    def generate_tex(self, *args, **kwargs): pass

class MockPackage:
    def __init__(self, *args, **kwargs): pass

class MockNoEscape:
    def __init__(self, *args, **kwargs): pass

class MockEnvironment:
    def __init__(self, *args, **kwargs): pass

# Patch modules before importing TestGeneratorAnalyzer
sys.modules['pylatex'] = type('MockPyLatex', (), {'Document': MockDocument, 'NoEscape': MockNoEscape, 'Package': MockPackage})
sys.modules['pylatex.base_classes'] = type('MockPyLatexBase', (), {'Environment': MockEnvironment})

from example.randomizer import TestGeneratorAnalyzer

@patch('builtins.open', new_callable=mock_open, read_data='{}')
def test_select_best_variants(mock_file):
    analyzer = TestGeneratorAnalyzer()

    # Setup original questions order
    analyzer.original_questions_order = ["Q1", "Q2", "Q3"]

    # Helper to create a question with one correct answer
    def make_q(q_text, correct_idx, total_ans=4):
        answers = []
        for i in range(total_ans):
            answers.append({"text": f"Ans{i}", "is_correct": i == correct_idx})
        return {"question_text": q_text, "answers": answers}

    # Variant 1: questions in original order, correct answers at index 0
    v1 = {
        "variant_id": "1",
        "questions": [
            make_q("Q1", 0),
            make_q("Q2", 0),
            make_q("Q3", 0)
        ]
    }

    # Variant 2: questions in reverse order, correct answers at index 3
    v2 = {
        "variant_id": "2",
        "questions": [
            make_q("Q3", 3),
            make_q("Q2", 3),
            make_q("Q1", 3)
        ]
    }

    # Variant 3: questions partially shuffled, correct answers mixed
    v3 = {
        "variant_id": "3",
        "questions": [
            make_q("Q2", 1),
            make_q("Q1", 2),
            make_q("Q3", 1)
        ]
    }

    potential_variants = [v1, v2, v3]

    # Verify logic
    # V1: 0 diffs -> Q score = 0.0. A score = 0.0. Total = 0.0
    # V2: 2 diffs (Q1, Q3) -> Q score = 0.666. A score = 1.0. Total = 0.833
    # V3: 2 diffs (Q1, Q2) -> Q score = 0.666. A score = 0.444. Total = 0.555
    # Order should be V2 > V3 > V1

    best_2 = analyzer.select_best_variants(potential_variants, {}, 2)
    assert len(best_2) == 2
    assert best_2[0]["variant_id"] == "2"
    assert best_2[1]["variant_id"] == "3"

    best_1 = analyzer.select_best_variants(potential_variants, {}, 1)
    assert len(best_1) == 1
    assert best_1[0]["variant_id"] == "2"

    best_all = analyzer.select_best_variants(potential_variants, {}, 5)
    assert len(best_all) == 3
    assert best_all[0]["variant_id"] == "2"
    assert best_all[1]["variant_id"] == "3"
    assert best_all[2]["variant_id"] == "1"

    # Edge case: Empty original questions order (should cause ZeroDivisionError if not handled, but code doesn't check it, wait, let's look at example/randomizer.py:398)
    # len(self.original_questions_order) is in denominator. We should avoid zero division, but if we pass empty, it will throw ZeroDivisionError.
    # In reality, evaluate_randomness_of_variants has: if not variants or not self.original_questions_order: return...
    # Let's test what happens if we set a single item in original_questions_order and see it selects

    analyzer.original_questions_order = ["Q1"]
    v_single1 = {
        "variant_id": "1",
        "questions": [make_q("Q1", 0)]
    }
    v_single2 = {
        "variant_id": "2",
        "questions": [make_q("Q1", 3)]
    }
    best_single = analyzer.select_best_variants([v_single1, v_single2], {}, 1)
    # Both have 0 Q score. v_single2 has 1.0 A score, v_single1 has 0.0 A score.
    # Expected: v_single2
    assert len(best_single) == 1
    assert best_single[0]["variant_id"] == "2"

    # Edge case: question with < 2 alternatives
    v_edge = {
        "variant_id": "edge",
        "questions": [
            {"question_text": "Q1", "answers": [{"text": "Ans0", "is_correct": True}]} # 1 alternative
        ]
    }
    best_edge = analyzer.select_best_variants([v_edge], {}, 1)
    assert len(best_edge) == 1
    assert best_edge[0]["variant_id"] == "edge"
