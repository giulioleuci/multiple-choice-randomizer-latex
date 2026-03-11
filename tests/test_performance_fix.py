import sys
from unittest.mock import MagicMock, patch
import pytest

@pytest.fixture
def analyzer_instance():
    """Fixture to provide TestGeneratorAnalyzer with mocked dependencies."""
    mocks = {
        "pandas": MagicMock(),
        "pylatex": MagicMock(),
        "pylatex.base_classes": MagicMock(),
        "matplotlib": MagicMock(),
        "matplotlib.pyplot": MagicMock(),
        "scipy": MagicMock(),
        "scipy.stats": MagicMock(),
        "numpy": MagicMock(),
        "openpyxl": MagicMock(),
    }
    class MockCommandBase:
        def __init__(self, *args, **kwargs): pass
    class MockEnvironment:
        def __init__(self, *args, **kwargs): pass
    mocks["pylatex.base_classes"].CommandBase = MockCommandBase
    mocks["pylatex.base_classes"].Environment = MockEnvironment

    with patch.dict(sys.modules, mocks):
        from randomizer import TestGeneratorAnalyzer
        with patch.object(TestGeneratorAnalyzer, "_load_config", return_value={}):
            analyzer = TestGeneratorAnalyzer()
            yield analyzer

def test_generate_student_excel_report_logic(analyzer_instance):
    """
    Test that generate_student_excel_report correctly processes data.
    """
    analyzer = analyzer_instance

    # Mock test_results
    analyzer.test_results = {
        "Student1": {
            "variant_id": "1",
            "correct_count": 1,
            "wrong_count": 0,
            "blank_count": 0,
            "correct_score": 4,
            "wrong_score": 0,
            "blank_score": 0,
            "total_score": 4,
            "max_possible_score": 4,
            "percentage": 100.0,
            "percentile": 100.0,
            "z_score": 0.0,
            "stanine": "S+",
            "answers": {
                "1": {"response": "A", "correct": "A"}
            }
        }
    }

    import pandas as pd
    # We patch pandas.DataFrame
    with patch('pandas.DataFrame') as MockDataFrame:
        mock_df = MagicMock()
        MockDataFrame.return_value = mock_df

        # Make _append return self to simplify for the current code
        mock_df._append.return_value = mock_df
        # Make sort_values return self
        mock_df.sort_values.return_value = mock_df
        # Make select_dtypes return a mock with columns
        mock_df.select_dtypes.return_value.columns = []

        # Call the method
        analyzer.generate_student_excel_report()

        # Verify DataFrame was called
        assert MockDataFrame.called

        # Verify it was saved to excel
        assert mock_df.to_excel.called
        assert mock_df.to_excel.call_args[0][0] == "report_students_summary.xlsx"
