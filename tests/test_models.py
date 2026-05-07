from core.models import AnswerChoice, Question, TestVariant, StudentSubmission

def test_answer_choice_initialization():
    choice = AnswerChoice(text="Paris", is_correct=True)
    assert choice.text == "Paris"
    assert choice.is_correct is True

    choice_default = AnswerChoice(text="London")
    assert choice_default.text == "London"
    assert choice_default.is_correct is False

def test_question_initialization():
    choice1 = AnswerChoice("A", True)
    choice2 = AnswerChoice("B", False)
    question = Question(
        question_text="What is the capital of France?",
        sheet_name="Capitals",
        answers=[choice1, choice2],
        num_columns_alternatives=2,
        punteggio_corretta=1.0,
        punteggio_errata=-0.5,
        punteggio_non_data=0.0
    )
    assert question.question_text == "What is the capital of France?"
    assert question.sheet_name == "Capitals"
    assert len(question.answers) == 2
    assert question.num_columns_alternatives == 2
    assert question.punteggio_corretta == 1.0
    assert question.punteggio_errata == -0.5
    assert question.punteggio_non_data == 0.0

def test_question_defaults():
    question = Question(
        question_text="Simple question",
        sheet_name="Sheet1",
        answers=[]
    )
    assert question.num_columns_alternatives == 1
    assert question.punteggio_corretta is None
    assert question.punteggio_errata is None
    assert question.punteggio_non_data is None

def test_test_variant_initialization():
    question = Question("Q1", "S1", [])
    variant = TestVariant(variant_id="V1", questions=[question])
    assert variant.variant_id == "V1"
    assert len(variant.questions) == 1
    assert variant.questions[0] == question

def test_student_submission_initialization():
    submission = StudentSubmission(
        student_id="S123",
        variant_id="V1",
        answers={"1": "A", "2": "C"}
    )
    assert submission.student_id == "S123"
    assert submission.variant_id == "V1"
    assert submission.answers == {"1": "A", "2": "C"}
