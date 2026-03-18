from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass
class AnswerChoice:
    text: str
    is_correct: bool = False

@dataclass
class Question:
    question_text: str
    sheet_name: str
    answers: List[AnswerChoice]
    num_columns_alternatives: int = 1
    punteggio_corretta: Optional[float] = None
    punteggio_errata: Optional[float] = None
    punteggio_non_data: Optional[float] = None

@dataclass
class TestVariant:
    variant_id: str
    questions: List[Question]

@dataclass
class StudentSubmission:
    student_id: str
    variant_id: str
    answers: Dict[str, str]  # Map of question number (as string) to selected answer letter
