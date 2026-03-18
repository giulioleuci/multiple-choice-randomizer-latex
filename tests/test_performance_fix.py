import pytest
import pandas as pd
from unittest.mock import patch
from io_handlers.excel_provider import generate_student_excel_report

@patch("io_handlers.excel_provider.pd.DataFrame.to_excel")
def test_generate_student_excel_report_logic(mock_to_excel):
    """Verify generate_student_excel_report handles logic."""
    test_results = {
        "S1": {
            "variant_id": "1",
            "correct_count": 2, "wrong_count": 1, "blank_count": 0,
            "correct_score": 8, "wrong_score": 0, "blank_score": 0,
            "total_score": 8, "max_possible_score": 12,
            "percentage": 66.67,
            "percentile": 50, "z_score": 0, "stanine": "C",
            "answers": {}
        }
    }
    generate_student_excel_report(test_results, "dummy.xlsx")
    mock_to_excel.assert_called_once()
