import numpy as np
import scipy.stats as stats
from typing import Dict, Any, Tuple

def _calculate_stanine(score: float, boundaries: np.ndarray) -> str:
    if score < boundaries[0]:
        return "F-"
    elif score < boundaries[1]:
        return "F"
    elif score < boundaries[2]:
        return "E"
    elif score < boundaries[3]:
        return "D"
    elif score < boundaries[4]:
        return "C"
    elif score < boundaries[5]:
        return "B"
    elif score < boundaries[6]:
        return "A"
    elif score < boundaries[7]:
        return "S"
    else:
        return "S+"

def calculate_basic_statistics(test_results: Dict[str, Any], passing_threshold: float) -> Tuple[float, float, Dict[str, Any]]:
    scores = [res["total_score"] for res in test_results.values()]
    percentages = [res["percentage"] for res in test_results.values()]

    avg_score = np.mean(scores)
    med_score = np.median(scores)
    std_dev = np.std(scores)
    min_score = min(scores)
    max_score = max(scores)

    threshold = passing_threshold * 100
    passed = sum(1 for p in percentages if p >= threshold)
    pass_rate = round((passed / len(percentages)) * 100, 2) if percentages else 0

    quartiles = np.percentile(scores, [25, 50, 75])

    avg_correct = np.mean([res["correct_score"] for res in test_results.values()])
    avg_wrong = np.mean([res["wrong_score"] for res in test_results.values()])
    avg_blank = np.mean([res["blank_score"] for res in test_results.values()])

    avg_correct_count = np.mean([res["correct_count"] for res in test_results.values()])
    avg_wrong_count = np.mean([res["wrong_count"] for res in test_results.values()])
    avg_blank_count = np.mean([res["blank_count"] for res in test_results.values()])

    analysis_results = {
        "num_students": len(scores),
        "average_score": round(avg_score, 2),
        "median_score": round(med_score, 2),
        "std_deviation": round(std_dev, 2),
        "min_score": round(min_score, 2),
        "max_score": round(max_score, 2),
        "quartiles": [round(q, 2) for q in quartiles],
        "passing_threshold": threshold,
        "pass_rate": pass_rate,
        "avg_correct_score": round(avg_correct, 2),
        "avg_wrong_score": round(avg_wrong, 2),
        "avg_blank_score": round(avg_blank, 2),
        "avg_correct_count": round(avg_correct_count, 2),
        "avg_wrong_count": round(avg_wrong_count, 2),
        "avg_blank_count": round(avg_blank_count, 2)
    }
    return avg_score, std_dev, analysis_results

def analyze_results(test_results: Dict[str, Any], passing_threshold: float) -> Dict[str, Any]:
    if not test_results:
        return {}

    scores = [res["total_score"] for res in test_results.values()]

    if not scores:
        return {}

    avg_score, std_dev, analysis_results = calculate_basic_statistics(test_results, passing_threshold)

    stanine_boundaries = np.percentile(scores, [4, 11, 23, 40, 60, 77, 89, 96])

    for student_id, result in test_results.items():
        z_score = (result["total_score"] - avg_score) / std_dev if std_dev != 0 else 0
        percentile = stats.percentileofscore(scores, result["total_score"])
        stanine = _calculate_stanine(result["total_score"], stanine_boundaries)

        test_results[student_id].update({
            "z_score": round(z_score, 2),
            "percentile": round(percentile, 2),
            "stanine": stanine
        })

    return analysis_results

def analyze_questions(test_results: Dict[str, Any], question_analytics: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, Any]]:
    if not question_analytics or not test_results:
        return question_analytics

    student_scores = [(student_id, result) for student_id, result in test_results.items()]
    student_scores.sort(key=lambda x: x[1]["total_score"], reverse=True)

    n = len(student_scores)
    upper_n = max(1, int(n * 0.27))
    lower_n = max(1, int(n * 0.27))

    upper_group = student_scores[:upper_n]
    lower_group = student_scores[-lower_n:]

    upper_correct_counts = {}
    for _, result in upper_group:
        seen_sheets = set()
        for ans_data in result["answers"].values():
            sheet_name = ans_data["sheet"]
            if sheet_name not in seen_sheets and ans_data["response"] != "blank" and \
               ans_data["response"].upper() == ans_data["correct"].upper():
                upper_correct_counts[sheet_name] = upper_correct_counts.get(sheet_name, 0) + 1
                seen_sheets.add(sheet_name)

    lower_correct_counts = {}
    for _, result in lower_group:
        seen_sheets = set()
        for ans_data in result["answers"].values():
            sheet_name = ans_data["sheet"]
            if sheet_name not in seen_sheets and ans_data["response"] != "blank" and \
               ans_data["response"].upper() == ans_data["correct"].upper():
                lower_correct_counts[sheet_name] = lower_correct_counts.get(sheet_name, 0) + 1
                seen_sheets.add(sheet_name)

    for sheet_name, stats_dict in question_analytics.items():
        total_answers = stats_dict["correct"] + stats_dict["wrong"] + stats_dict["blank"]
        if total_answers == 0:
            continue

        correct_pct = round((stats_dict["correct"] / total_answers) * 100, 2)
        wrong_pct = round((stats_dict["wrong"] / total_answers) * 100, 2)
        blank_pct = round((stats_dict["blank"] / total_answers) * 100, 2)

        difficulty = 1.0 - (stats_dict["correct"] / total_answers)

        upper_correct = upper_correct_counts.get(sheet_name, 0)
        lower_correct = lower_correct_counts.get(sheet_name, 0)

        p_upper = upper_correct / upper_n if upper_n > 0 else 0
        p_lower = lower_correct / lower_n if lower_n > 0 else 0
        discrimination = p_upper - p_lower

        question_analytics[sheet_name].update({
            "total_answers": total_answers,
            "correct_pct": correct_pct,
            "wrong_pct": wrong_pct,
            "blank_pct": blank_pct,
            "difficulty": round(difficulty, 2),
            "discrimination": round(discrimination, 2)
        })

    return question_analytics
