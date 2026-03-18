import json
import re

class AppConfig:
    def __init__(self, config_file: str = "config.json"):
        self.raw_config = self._load_config(config_file)
        self.default_correct_score = self.raw_config.get("default_correct_score", 4)
        self.default_wrong_score = self.raw_config.get("default_wrong_score", 0)
        self.default_no_answer_score = self.raw_config.get("default_no_answer_score", 1)
        self.passing_threshold = self.raw_config.get("passing_threshold", 0.58)

    def _load_config(self, config_file: str) -> dict:
        """Carica la configurazione da JSON (rimuovendo eventuali commenti in stile C)."""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
            return json.loads(content)
        except FileNotFoundError:
            raise FileNotFoundError(f"File di configurazione non trovato: {config_file}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Errore nella lettura del JSON: {str(e)}")

    def get(self, key, default=None):
        return self.raw_config.get(key, default)
