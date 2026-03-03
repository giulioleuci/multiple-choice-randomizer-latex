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
    # Mock specific pylatex classes if needed, similar to test_latex_custom_command.py
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

def test_correct_tests_early_return(analyzer_instance, capsys):
    """
    Test that correct_tests returns early and prints a message
    when student_responses is None.
    """
    analyzer = analyzer_instance
    analyzer.student_responses = None

    # Call the method
    analyzer.correct_tests()

    # Capture output
    captured = capsys.readouterr()

    # Assertions
    assert "Nessuna risposta studentesca caricata." in captured.out
    # Verify that it didn't proceed to initialize other variables or loops
    # (Implicitly verified by no errors being raised for missing mocks if it had continued)
