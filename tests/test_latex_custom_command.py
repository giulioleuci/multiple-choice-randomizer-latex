import sys
from unittest.mock import MagicMock, patch
import pytest

# Define a real class for CommandBase so we can patch its __init__
class MockCommandBase:
    def __init__(self, command, arguments=None, options=None, extra_arguments=None):
        pass

@pytest.fixture(scope="module")
def latex_custom_command_class():
    """Fixture to provide LatexCustomCommand with mocked dependencies."""
    # We need to mock all top-level imports in randomizer.py
    mocks = {
        "pandas": MagicMock(),
        "pylatex": MagicMock(),
        "pylatex.base_classes": MagicMock(),
        "matplotlib": MagicMock(),
        "matplotlib.pyplot": MagicMock(),
        "matplotlib.colors": MagicMock(),
        "scipy": MagicMock(),
        "scipy.stats": MagicMock(),
        "numpy": MagicMock(),
    }
    mocks["pylatex.base_classes"].CommandBase = MockCommandBase

    with patch.dict(sys.modules, mocks):
        # Import inside the patch context
        from randomizer import LatexCustomCommand
        yield LatexCustomCommand

class TestLatexCustomCommand:
    def test_init_all_arguments(self, latex_custom_command_class):
        """Test initialization with all arguments provided."""
        LatexCustomCommand = latex_custom_command_class
        command_name = "testcommand"
        args = ["arg1", "arg2"]
        opts = ["opt1", "opt2"]
        extra = "extra_arg"

        with patch.object(MockCommandBase, '__init__', return_value=None) as mock_init:
            cmd = LatexCustomCommand(
                command=command_name,
                arguments=args,
                options=opts,
                extra_arguments=extra
            )

            mock_init.assert_called_once_with(
                command_name,
                arguments=args,
                options=opts,
                extra_arguments=extra
            )

    def test_init_default_arguments(self, latex_custom_command_class):
        """Test initialization with only the command name (defaults)."""
        LatexCustomCommand = latex_custom_command_class
        command_name = "testcommand"

        with patch.object(MockCommandBase, '__init__', return_value=None) as mock_init:
            cmd = LatexCustomCommand(command=command_name)

            mock_init.assert_called_once_with(
                command_name,
                arguments=None,
                options=None,
                extra_arguments=None
            )

    def test_init_positional_arguments(self, latex_custom_command_class):
        """Test initialization with positional arguments."""
        LatexCustomCommand = latex_custom_command_class
        command_name = "testcommand"
        args = ["arg1"]
        opts = ["opt1"]
        extra = "extra1"

        with patch.object(MockCommandBase, '__init__', return_value=None) as mock_init:
            cmd = LatexCustomCommand(command_name, args, opts, extra)

            mock_init.assert_called_once_with(
                command_name,
                arguments=args,
                options=opts,
                extra_arguments=extra
            )

    def test_init_with_none(self, latex_custom_command_class):
        """Test initialization explicitly passing None."""
        LatexCustomCommand = latex_custom_command_class
        command_name = "testcommand"

        with patch.object(MockCommandBase, '__init__', return_value=None) as mock_init:
            cmd = LatexCustomCommand(
                command=command_name,
                arguments=None,
                options=None,
                extra_arguments=None
            )

            mock_init.assert_called_once_with(
                command_name,
                arguments=None,
                options=None,
                extra_arguments=None
            )
