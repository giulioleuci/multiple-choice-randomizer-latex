import random
from core.models import Question, AnswerChoice
from core.logic import generate_test_variants

def test_generate_test_variants_deterministic():
    rng1 = random.Random(42)
    rng2 = random.Random(42)

    questions = [
        Question("Q1", "S1", [AnswerChoice("A", True), AnswerChoice("B", False)]),
        Question("Q2", "S2", [AnswerChoice("C", True), AnswerChoice("D", False)]),
        Question("Q3", "S3", [AnswerChoice("E", True), AnswerChoice("F", False)])
    ]

    variants1 = generate_test_variants(questions, 2, rng1)
    variants2 = generate_test_variants(questions, 2, rng2)

    assert len(variants1) == 2
    assert len(variants2) == 2

    # Verify that the exact same random state produces the same shuffles
    for v1, v2 in zip(variants1, variants2):
        assert [q.question_text for q in v1.questions] == [q.question_text for q in v2.questions]
        for q1, q2 in zip(v1.questions, v2.questions):
            assert [a.text for a in q1.answers] == [a.text for a in q2.answers]

    # Verify original list is not mutated
    assert questions[0].question_text == "Q1"
    assert questions[1].question_text == "Q2"
    assert questions[2].question_text == "Q3"
