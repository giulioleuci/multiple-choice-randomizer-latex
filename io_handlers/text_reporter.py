import os
import json
import re
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Any
from core.models import TestVariant
from core.config import AppConfig

def generate_answer_keys_report(variants: List[TestVariant], config: AppConfig) -> tuple:
    label_style = config.get('choice_label_format', 'letters_upper')
    report_lines = []

    variant_answer_keys = {}
    variant_question_mappings = {}

    for variant in variants:
        variant_id = variant.variant_id
        key_mapping = {}
        question_mapping = {}

        for q_idx, question in enumerate(variant.questions):
            question_num = str(q_idx + 1)
            sheet_name = question.sheet_name
            question_mapping[question_num] = sheet_name

            correct_idx = next((i for i, ans in enumerate(question.answers) if ans.is_correct), 0)

            if label_style == "letters_upper":
                key = chr(ord('A') + correct_idx)
            elif label_style == "letters_lower":
                key = chr(ord('a') + correct_idx)
            else:
                key = str(correct_idx + 1)

            key_mapping[question_num] = key

        variant_answer_keys[variant_id] = key_mapping
        variant_question_mappings[variant_id] = question_mapping

        line = f"Variante {variant_id}: " + " ".join([f"Domanda {qnum}: {key_mapping[qnum]} ({question_mapping[qnum]})" for qnum in sorted(key_mapping.keys(), key=int)])
        report_lines.append(line)

    with open("answer_keys_report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    mappings_data = {
        "variant_answer_keys": variant_answer_keys,
        "variant_question_mappings": variant_question_mappings
    }
    with open("question_mappings.json", "w", encoding="utf-8") as f:
        json.dump(mappings_data, f, indent=4)

    return variant_answer_keys, variant_question_mappings

def _create_question_pie_chart(sheet_name: str, stats: Dict[str, Any]):
    plt.figure(figsize=(8, 6))
    labels = ['Corrette', 'Errate', 'Non Date']
    sizes = [stats.get('correct_pct', 0), stats.get('wrong_pct', 0), stats.get('blank_pct', 0)]
    colors = ['green', 'red', 'gray']
    explode = (0.1, 0, 0)
    plt.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%', shadow=True, startangle=140)
    plt.axis('equal')
    plt.title(f'Distribuzione Risposte - Domanda: {sheet_name}')
    safe_name = re.sub(r'[\\/*?:"<>|]', "", sheet_name)
    plt.savefig(os.path.join("report_questions", f"question_{safe_name}.png"), dpi=300, bbox_inches='tight')
    plt.close()

def _create_stacked_bar_chart(data: Dict[str, List[Any]]):
    plt.figure(figsize=(12, 8))
    domande = data["domande"]
    corrette = np.array(data["correct"])
    non_date = np.array(data["blank"])
    errate = np.array(data["wrong"])
    bar_width = 0.8
    if corrette.sum() + non_date.sum() + errate.sum() > 100 * len(domande):
        total = corrette + non_date + errate
        corrette = (corrette / total) * 100
        non_date = (non_date / total) * 100
        errate = (errate / total) * 100
    indices = np.arange(len(domande))
    plt.bar(indices, corrette, bar_width, color='green', label='Corrette')
    plt.bar(indices, non_date, bar_width, bottom=corrette, color='gray', label='Non Date')
    plt.bar(indices, errate, bar_width, bottom=corrette+non_date, color='red', label='Errate')
    plt.xlabel('Domande')
    plt.ylabel('Percentuale (%)')
    plt.title('Distribuzione Risposte per Domanda')
    plt.xticks(indices, domande, rotation=45, ha='right')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join("report_questions", "all_questions_stacked.png"), dpi=300, bbox_inches='tight')
    plt.close()

def generate_question_report(question_analytics: Dict[str, Dict[str, Any]], analysis_results: Dict[str, Any]):
    if not question_analytics:
        return

    os.makedirs("report_questions", exist_ok=True)
    lines = ["=== Report delle Domande ===\n"]
    lines.append(f"Numero totale di domande: {len(question_analytics)}")
    lines.append(f"Numero totale di studenti: {analysis_results.get('num_students', 0)}")
    lines.append(f"Punteggio medio del test: {analysis_results.get('average_score', 0)}\n")
    lines.append("Dettaglio per Domanda:")

    all_questions_data = {"domande": [], "correct": [], "blank": [], "wrong": []}

    for sheet_name, stats in sorted(question_analytics.items()):
        lines.append(f"\n== Domanda: {sheet_name} ==")
        lines.append(f"Risposte corrette: {stats.get('correct', 0)} ({stats.get('correct_pct', 0)}%)")
        lines.append(f"Risposte errate: {stats.get('wrong', 0)} ({stats.get('wrong_pct', 0)}%)")
        lines.append(f"Risposte non date: {stats.get('blank', 0)} ({stats.get('blank_pct', 0)}%)")
        lines.append(f"Indice di difficoltà: {stats.get('difficulty', 0)} (0=facile, 1=difficile)")
        lines.append(f"Indice di discriminazione: {stats.get('discrimination', 0)} (-1=negativo, 1=positivo)")

        difficulty_rating = "Facile" if stats.get('difficulty', 0) < 0.3 else ("Media" if stats.get('difficulty', 0) < 0.7 else "Difficile")
        disc = stats.get('discrimination', 0)
        discrimination_rating = "Negativa (problematica)" if disc < 0 else ("Scarsa" if disc < 0.2 else ("Buona" if disc < 0.4 else "Eccellente"))

        lines.append(f"Valutazione difficoltà: {difficulty_rating}")
        lines.append(f"Valutazione discriminazione: {discrimination_rating}")

        _create_question_pie_chart(sheet_name, stats)
        all_questions_data["domande"].append(sheet_name)
        all_questions_data["correct"].append(stats.get('correct_pct', 0))
        all_questions_data["blank"].append(stats.get('blank_pct', 0))
        all_questions_data["wrong"].append(stats.get('wrong_pct', 0))

    _create_stacked_bar_chart(all_questions_data)
    with open(os.path.join("report_questions", "report_quest.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def _create_score_distribution_chart(test_results: Dict[str, Any], analysis_results: Dict[str, Any]):
    scores = [res["total_score"] for res in test_results.values()]
    plt.figure(figsize=(10, 6))
    plt.hist(scores, bins=10, color='skyblue', edgecolor='black', alpha=0.7)
    plt.axvline(analysis_results.get('average_score', 0), color='red', linestyle='--', linewidth=2, label='Media')
    plt.axvline(analysis_results.get('median_score', 0), color='green', linestyle='-', linewidth=2, label='Mediana')
    max_scores = [res["max_possible_score"] for res in test_results.values()]
    avg_max = np.mean(max_scores) if max_scores else 0
    pass_threshold = avg_max * (analysis_results.get('passing_threshold', 0) / 100)
    plt.axvline(pass_threshold, color='orange', linestyle='-.', linewidth=2, label='Soglia Sufficienza')
    plt.xlabel('Punteggio')
    plt.ylabel('Numero di Studenti')
    plt.title('Distribuzione dei Punteggi')
    plt.legend()
    plt.tight_layout()
    os.makedirs("report_questions", exist_ok=True)
    plt.savefig(os.path.join("report_questions", "score_distribution.png"), dpi=300, bbox_inches='tight')
    plt.close()

def generate_student_report(test_results: Dict[str, Any], analysis_results: Dict[str, Any]):
    if not test_results:
        return

    lines = ["=== Report degli Studenti ===\n", "Statistiche Generali:"]
    lines.append(f"Numero di studenti: {analysis_results.get('num_students', 0)}")
    lines.append(f"Punteggio medio: {analysis_results.get('average_score', 0)}")
    lines.append(f"Punteggio mediano: {analysis_results.get('median_score', 0)}")
    lines.append(f"Deviazione standard: {analysis_results.get('std_deviation', 0)}")
    lines.append(f"Punteggio minimo: {analysis_results.get('min_score', 0)}")
    lines.append(f"Punteggio massimo: {analysis_results.get('max_score', 0)}")
    lines.append(f"Quartili (25%, 50%, 75%): {analysis_results.get('quartiles', [0, 0, 0])}")
    lines.append(f"Soglia di sufficienza: {analysis_results.get('passing_threshold', 0)}%")
    lines.append(f"Percentuale di promossi: {analysis_results.get('pass_rate', 0)}%")
    lines.append(f"Media risposte corrette: {analysis_results.get('avg_correct_count', 0)}")
    lines.append(f"Media risposte errate: {analysis_results.get('avg_wrong_count', 0)}")
    lines.append(f"Media risposte non date: {analysis_results.get('avg_blank_count', 0)}")
    lines.append(f"Media punti risposte corrette: {analysis_results.get('avg_correct_score', 0)}")
    lines.append(f"Media punti risposte errate: {analysis_results.get('avg_wrong_score', 0)}")
    lines.append(f"Media punti risposte non date: {analysis_results.get('avg_blank_score', 0)}\n")

    _create_score_distribution_chart(test_results, analysis_results)

    lines.append("\nDettaglio per Studente:")
    lines.append("Student ID | Var | Corr | Err | ND | P.Corr | P.Err | P.ND | Tot | Max | % | %ile | Z | Stanine")
    lines.append("-" * 100)

    # Sort results
    sorted_results = sorted(test_results.items(), key=lambda x: x[1]['total_score'], reverse=True)

    for student_id, res in sorted_results:
        line = f"{student_id} | {res.get('variant_id')} | {res.get('correct_count')} | {res.get('wrong_count')} | {res.get('blank_count')} | "
        line += f"{res.get('correct_score')} | {res.get('wrong_score')} | {res.get('blank_score')} | {res.get('total_score')} | {res.get('max_possible_score')} | "
        line += f"{res.get('percentage')}% | {res.get('percentile', 0)} | {res.get('z_score', 0)} | {res.get('stanine', '')}"
        lines.append(line)

    with open("report_students.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def generate_teacher_report(analysis_results: Dict[str, Any], variant_answer_keys: Dict[str, Dict[str, str]], variant_question_mappings: Dict[str, Dict[str, str]]):
    lines = []
    lines.append("=== Report Sintetico per l'Insegnante ===")
    lines.append(f"Numero di studenti: {analysis_results.get('num_students', 0)}")
    lines.append(f"Punteggio medio: {analysis_results.get('average_score', 0)}")
    lines.append(f"Mediana: {analysis_results.get('median_score', 0)}")
    lines.append(f"Deviazione standard: {analysis_results.get('std_deviation', 0)}")
    lines.append(f"Percentuale di promossi: {analysis_results.get('pass_rate', 0)}%")
    lines.append("\nDettaglio per variante:")

    for variant_id in variant_answer_keys.keys():
        key_mapping = variant_answer_keys[variant_id]
        question_mapping = variant_question_mappings[variant_id]
        lines.append(f"\nVariante {variant_id}:")
        for q_num in sorted(key_mapping.keys(), key=int):
            sheet_name = question_mapping.get(q_num, "Sconosciuta")
            answer_key = key_mapping.get(q_num, "?")
            lines.append(f"Domanda {q_num}: Risposta {answer_key} (Foglio: {sheet_name})")

    with open("teacher_report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def _generate_student_report_text(test_results: Dict[str, Any]) -> str:
    all_lines = ["=== Report Dettagliato degli Studenti ===\n"]
    student_ids = sorted(test_results.keys(), key=lambda s: test_results[s]["total_score"], reverse=True)

    for student_id in student_ids:
        result = test_results[student_id]
        variant_id = result["variant_id"]

        lines = [f"\n---- Studente: {student_id} ----"]
        lines.append(f"Variante del test: {variant_id}")
        lines.append(f"\nPunteggio totale: {result['total_score']} su {result['max_possible_score']} ({result['percentage']}%)")
        lines.append(f"Punti da risposte corrette: {result['correct_score']} (n. risposte: {result['correct_count']})")
        lines.append(f"Punti da risposte errate: {result['wrong_score']} (n. risposte: {result['wrong_count']})")
        lines.append(f"Punti da risposte non date: {result['blank_score']} (n. risposte: {result['blank_count']})")

        lines.append(f"\nConfrontato con la classe:")
        lines.append(f"Percentile: {result.get('percentile', 0)} (0-100)")
        lines.append(f"Z-Score: {result.get('z_score', 0)} (distanza dalla media in unità di deviazione standard)")
        lines.append(f"Stanine: {result.get('stanine', '')} (F- = peggiore, S+ = migliore)")

        lines.append("\nDettaglio risposte:")
        answer_details = result.get("answers", {})

        for q_num in sorted(answer_details.keys(), key=int):
            ans_data = answer_details[q_num]
            sheet_name = ans_data.get("sheet", "Sconosciuta")
            student_response = ans_data.get("response", "")
            correct_answer = ans_data.get("correct", "")
            points = ans_data.get("points", 0)

            if student_response == "blank":
                status = f"NON DATA (punti: {points})"
            elif student_response.upper() == correct_answer.upper():
                status = f"CORRETTA (punti: {points})"
            else:
                status = f"ERRATA - Risposta corretta: {correct_answer} (punti: {points})"

            lines.append(f"Domanda {q_num} ({sheet_name}): Risposta: {student_response} - {status}")

        all_lines.extend(lines)

    return "\n".join(all_lines)

def generate_student_reports(test_results: Dict[str, Any]):
    if not test_results:
        return
    report_text = _generate_student_report_text(test_results)
    with open("report_students_detailed.txt", "w", encoding="utf-8") as f:
        f.write(report_text)
