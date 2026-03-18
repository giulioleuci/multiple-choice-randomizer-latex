import subprocess
from unittest.mock import patch, MagicMock
from io_handlers.latex_emitter import compile_latex_to_pdf

def test_security_fix_no_shell_escape():
    """Verify that pdflatex is called with -no-shell-escape."""
    with patch("subprocess.run") as mock_run:
        mock_latex_obj = MagicMock()
        compile_latex_to_pdf(mock_latex_obj, "test_output")

        # Check all calls to subprocess.run
        pdflatex_calls = [call for call in mock_run.call_args_list if "pdflatex" in call.args[0]]

        for call in pdflatex_calls:
            args = call.args[0]
            assert "-no-shell-escape" in args, f"pdflatex called without -no-shell-escape: {args}"
