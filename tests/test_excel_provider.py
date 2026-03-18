import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from io_handlers.excel_provider import load_questions_from_excel, _parse_row

def test_parse_row_edge_cases():
    data = {
        "Testo della domanda": "What is 2+2?",
        "Risposta corretta": "4",
        "Alternativa 1": "3",
        "Alternativa 2": None,
        "Alternativa 3": " ",
        "Punteggio corretta": "1.5",
        "Punteggio errata": "-0.5",
        "Punteggio non data": "invalid_float"
    }
    series = pd.Series(data)

    question = _parse_row(series, "Math101", list(data.keys()))

    assert question.question_text == "What is 2+2?"
    assert len(question.answers) == 2
    assert question.answers[0].text == "4"
    assert question.answers[0].is_correct is True
    assert question.answers[1].text == "3"
    assert question.answers[1].is_correct is False

    assert question.punteggio_corretta == 1.5
    assert question.punteggio_errata == -0.5
    assert question.punteggio_non_data is None

@patch("io_handlers.excel_provider.pd.read_excel")
def test_load_questions_empty_rows(mock_read_excel):
    df1 = pd.DataFrame({
        "Testo della domanda": ["Valid Q", "", None],
        "Risposta corretta": ["Valid A", "A", "B"]
    })

    df2 = pd.DataFrame({
        "Testo della domanda": ["Missing correct ans"],
        "Risposta corretta": [None]
    })

    mock_read_excel.return_value = {"Sheet1": df1, "Sheet2": df2}

    questions = load_questions_from_excel("dummy.xlsx")
    assert len(questions) == 1
    assert questions[0].question_text == "Valid Q"
