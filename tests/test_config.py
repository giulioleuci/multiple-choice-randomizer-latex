import pytest
from unittest.mock import patch, mock_open
from core.config import AppConfig

def test_config_valid_json():
    json_data = '''
    {
        /* This is a comment */
        "default_correct_score": 5,
        "default_wrong_score": -1
    }
    '''
    with patch("builtins.open", mock_open(read_data=json_data)):
        config = AppConfig("dummy.json")
        assert config.default_correct_score == 5
        assert config.default_wrong_score == -1
        assert config.default_no_answer_score == 1 # fallback to default

def test_config_invalid_json():
    json_data = '''
    {
        "default_correct_score": 5,
    }
    '''
    with patch("builtins.open", mock_open(read_data=json_data)):
        with pytest.raises(ValueError, match="Errore nella lettura del JSON"):
            AppConfig("dummy.json")

def test_config_file_not_found():
    with patch("builtins.open", side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError, match="File di configurazione non trovato"):
            AppConfig("dummy.json")
