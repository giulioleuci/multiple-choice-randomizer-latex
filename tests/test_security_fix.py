import sys
import os
from unittest.mock import MagicMock, patch
import pytest

def create_analyzer_mock(module_path):
    """Utility to provide TestGeneratorAnalyzer with mocked dependencies."""
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

    # We need to be careful with sys.modules if we want to test both files
    # However, they are supposed to be identical.

    with patch.dict(sys.modules, mocks):
        # Using importlib to import from path might be better but let's stick to what's used in existing tests
        if module_path == "randomizer":
            from randomizer import TestGeneratorAnalyzer
        else:
            # For example/randomizer.py, we might need a different approach if it's already in sys.modules
            import importlib.util
            spec = importlib.util.spec_from_file_location("randomizer_example", module_path)
            foo = importlib.util.module_from_spec(spec)
            sys.modules["randomizer_example"] = foo
            spec.loader.exec_module(foo)
            TestGeneratorAnalyzer = foo.TestGeneratorAnalyzer

        with patch.object(TestGeneratorAnalyzer, "_load_config", return_value={}):
            analyzer = TestGeneratorAnalyzer()
            return analyzer

def test_security_fix_no_shell_escape_root():
    """Verify that pdflatex is called with -no-shell-escape in randomizer.py."""
    analyzer = create_analyzer_mock("randomizer")

    with patch("subprocess.run") as mock_run:
        mock_latex_obj = MagicMock()
        analyzer.compile_latex_to_pdf(mock_latex_obj, "test_output")

        # Check all calls to subprocess.run
        pdflatex_calls = [call for call in mock_run.call_args_list if "pdflatex" in call.args[0]]

        for call in pdflatex_calls:
            args = call.args[0]
            assert "-no-shell-escape" in args, f"pdflatex called without -no-shell-escape: {args}"

def test_security_fix_no_shell_escape_example():
    """Verify that pdflatex is called with -no-shell-escape in example/randomizer.py."""
    analyzer = create_analyzer_mock("example/randomizer.py")

    with patch("subprocess.run") as mock_run:
        mock_latex_obj = MagicMock()
        analyzer.compile_latex_to_pdf(mock_latex_obj, "test_output")

        # Check all calls to subprocess.run
        pdflatex_calls = [call for call in mock_run.call_args_list if "pdflatex" in call.args[0]]

        for call in pdflatex_calls:
            args = call.args[0]
            assert "-no-shell-escape" in args, f"pdflatex called without -no-shell-escape in example: {args}"
