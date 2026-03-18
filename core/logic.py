import copy
import numpy as np
from typing import List, Dict, Any, Tuple
from core.models import Question, TestVariant, StudentSubmission
from core.config import AppConfig

def generate_test_variants(questions_data: List[Question], num_variants: int, rng) -> List[TestVariant]:
    """
    Genera num_variants varianti del test randomizzando l'ordine delle domande (da fogli diversi)
    e l'ordine delle risposte in ciascuna domanda, senza mutare questions_data.
    """
    if not questions_data:
        return []
    variants = []
    for i in range(num_variants):
        variant_questions = copy.deepcopy(questions_data)
        rng.shuffle(variant_questions)
        for question in variant_questions:
            rng.shuffle(question.answers)
        variant = TestVariant(
            variant_id=str(i + 1),
            questions=variant_questions
        )
        variants.append(variant)
    return variants

def evaluate_randomness_of_variants(variants: List[TestVariant], original_questions_order: List[str]) -> Dict[str, float]:
    """
    Calcola le metriche di randomicità.
    """
    if not variants or not original_questions_order:
        return {"question_order_randomness": 0, "answer_order_randomness": 0, "combined_randomness": 0}
    num_questions = len(original_questions_order)
    question_order_scores = []
    for variant in variants:
        variant_order = [q.question_text for q in variant.questions]
        diff_count = sum(1 for orig, var in zip(original_questions_order, variant_order) if orig != var)
        question_order_scores.append(diff_count / num_questions)
    question_order_randomness = np.mean(question_order_scores)

    answer_positions = {}
    q_alternatives = {}
    for variant in variants:
        for question in variant.questions:
            q_text = question.question_text
            correct_index = next((i for i, ans in enumerate(question.answers) if ans.is_correct), 0)
            if q_text not in answer_positions:
                answer_positions[q_text] = []
                q_alternatives[q_text] = len(question.answers)
            answer_positions[q_text].append(correct_index)

    normalized_stds = []
    for q_text, positions in answer_positions.items():
        arr = np.array(positions)
        if len(arr) > 1 and (max(arr) - min(arr)) > 0:
            std = np.std(arr)
            n_alternatives = q_alternatives.get(q_text, 1)
            norm_std = std / (n_alternatives - 1) if n_alternatives > 1 else 0
            normalized_stds.append(norm_std)
        else:
            normalized_stds.append(0)

    answer_order_randomness = np.mean(normalized_stds) if normalized_stds else 0
    combined_randomness = (question_order_randomness + answer_order_randomness) / 2

    return {
        "question_order_randomness": round(question_order_randomness, 2),
        "answer_order_randomness": round(answer_order_randomness, 2),
        "combined_randomness": round(combined_randomness, 2)
    }

def select_best_variants(potential_variants: List[TestVariant], original_questions_order: List[str], num_variants: int) -> List[TestVariant]:
    """
    Seleziona le migliori varianti in base a uno score.
    """
    scores = []
    for variant in potential_variants:
        variant_order = [q.question_text for q in variant.questions]
        diff_count = sum(1 for orig, var in zip(original_questions_order, variant_order) if orig != var)
        question_order_score = diff_count / len(original_questions_order) if original_questions_order else 0
        answer_scores = []
        for question in variant.questions:
            n_alternatives = len(question.answers)
            correct_index = next((i for i, ans in enumerate(question.answers) if ans.is_correct), 0)
            score = (correct_index / (n_alternatives - 1)) if n_alternatives > 1 else 0
            answer_scores.append(score)
        answer_order_score = np.mean(answer_scores) if answer_scores else 0
        variant_score = (question_order_score + answer_order_score) / 2
        scores.append((variant_score, variant))
    scores.sort(key=lambda x: x[0], reverse=True)
    return [v for score, v in scores[:num_variants]]

def score_single_student(submission: StudentSubmission,
                         key_mapping: Dict[str, str],
                         question_mapping: Dict[str, str],
                         question_data_map: Dict[str, Question],
                         config: AppConfig,
                         question_stats: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
    """
    Calcola i punteggi per un singolo studente e aggiorna le statistiche delle domande in question_stats.
    """
    correct_count = 0
    wrong_count = 0
    blank_count = 0
    correct_score = 0
    wrong_score = 0
    blank_score = 0
    max_possible_score = 0
    student_answers = {}

    for col, student_ans in submission.answers.items():
        if col in key_mapping and col in question_mapping:
            correct_letter = key_mapping[col]
            sheet_name = question_mapping[col]
            question_data = question_data_map.get(sheet_name)

            if question_data:
                punto_corretta = question_data.punteggio_corretta if question_data.punteggio_corretta is not None else config.default_correct_score
                punto_errata = question_data.punteggio_errata if question_data.punteggio_errata is not None else config.default_wrong_score
                punto_non_data = question_data.punteggio_non_data if question_data.punteggio_non_data is not None else config.default_no_answer_score
            else:
                punto_corretta = config.default_correct_score
                punto_errata = config.default_wrong_score
                punto_non_data = config.default_no_answer_score

            max_possible_score += punto_corretta

            if not student_ans or student_ans == "nan":  # Risposta non data
                blank_count += 1
                blank_score += punto_non_data
                student_answers[col] = {"sheet": sheet_name, "response": "blank", "correct": correct_letter, "points": punto_non_data}
                question_stats[sheet_name]["blank"] += 1
            elif student_ans.upper() == correct_letter.upper():
                correct_count += 1
                correct_score += punto_corretta
                student_answers[col] = {"sheet": sheet_name, "response": student_ans, "correct": correct_letter, "points": punto_corretta}
                question_stats[sheet_name]["correct"] += 1
            else:
                wrong_count += 1
                wrong_score += punto_errata
                student_answers[col] = {"sheet": sheet_name, "response": student_ans, "correct": correct_letter, "points": punto_errata}
                question_stats[sheet_name]["wrong"] += 1

    total_score = correct_score + wrong_score + blank_score
    percentage = round((total_score / max_possible_score) * 100, 2) if max_possible_score > 0 else 0

    return {
        "correct_count": correct_count,
        "wrong_count": wrong_count,
        "blank_count": blank_count,
        "correct_score": correct_score,
        "wrong_score": wrong_score,
        "blank_score": blank_score,
        "total_score": total_score,
        "max_possible_score": max_possible_score,
        "percentage": percentage,
        "answers": student_answers,
        "variant_id": submission.variant_id
    }

def correct_tests(submissions: List[StudentSubmission],
                  variants: List[TestVariant],
                  variant_answer_keys: Dict[str, Dict[str, str]],
                  variant_question_mappings: Dict[str, Dict[str, str]],
                  config: AppConfig) -> Tuple[Dict[str, Any], Dict[str, Dict[str, int]]]:
    """
    Corregge i test per una lista di studenti.
    """
    if not submissions:
        return {}, {}

    from collections import defaultdict
    question_stats = defaultdict(lambda: {"correct": 0, "wrong": 0, "blank": 0})

    variant_question_data_maps = {}
    for variant in variants:
        q_map = {}
        for q in variant.questions:
            q_map[q.sheet_name] = q
        variant_question_data_maps[variant.variant_id] = q_map

    test_results = {}

    for submission in submissions:
        variant_id = submission.variant_id
        if variant_id not in variant_answer_keys or variant_id not in variant_question_mappings:
            continue

        key_mapping = variant_answer_keys[variant_id]
        question_mapping = variant_question_mappings[variant_id]
        question_data_map = variant_question_data_maps.get(variant_id, {})

        result = score_single_student(submission, key_mapping, question_mapping, question_data_map, config, question_stats)
        test_results[submission.student_id] = result

    return test_results, dict(question_stats)
