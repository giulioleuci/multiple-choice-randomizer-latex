import os
import json
import argparse
import subprocess
import secrets
from utils.logger import get_logger
from utils.fs_ops import ensure_dir
from core.config import AppConfig
from core.logic import generate_test_variants, evaluate_randomness_of_variants, select_best_variants, correct_tests
from core.analyzer import analyze_results, analyze_questions
from core.models import TestVariant
from io_handlers.excel_provider import load_questions_from_excel, load_student_answers_from_excel, create_student_answers_template, generate_student_excel_report
from io_handlers.latex_emitter import _generate_latex_for_variant, compile_latex_to_pdf
from io_handlers.text_reporter import generate_answer_keys_report, generate_question_report, generate_student_report, generate_teacher_report, generate_student_reports

logger = get_logger("TestGeneratorAnalyzer")

def check_pdflatex():
    try:
        subprocess.run(["pdflatex", "--version"], capture_output=True, check=False)
    except Exception:
        raise RuntimeError("pdflatex non trovato nel sistema")

def check_files(required_files):
    for f in required_files:
        if not os.path.exists(f):
            raise FileNotFoundError(f"File richiesto non trovato: {f}")

def phase1():
    ensure_dir("tests_tex")
    ensure_dir("tests_pdf")
    check_files(["config.json", "questions.xlsx"])
    check_pdflatex()

    config = AppConfig()

    questions_data = load_questions_from_excel("questions.xlsx")
    original_questions_order = [q.question_text for q in questions_data]
    logger.info(f"Domande caricate da 'questions.xlsx': {len(questions_data)} domande trovate.")

    num_potential_variants = config.get('num_potential_variants_for_randomness_check', 10)
    secure_rng = secrets.SystemRandom()
    potential_variants = generate_test_variants(questions_data, num_potential_variants, secure_rng)
    logger.info(f"{num_potential_variants} varianti generate.")

    randomness_metrics = evaluate_randomness_of_variants(potential_variants, original_questions_order)
    logger.info("\n=== Metriche di Randomicità ===")
    for metric, value in randomness_metrics.items():
        logger.info(f"{metric}: {value}")

    num_variants = config.get('num_variants', 1)
    selected_variants = select_best_variants(potential_variants, original_questions_order, num_variants)
    logger.info(f"{num_variants} varianti selezionate sulla base dello score.")

    for variant in selected_variants:
        output_base = os.path.join("tests_tex", f"test_variant_{variant.variant_id}")
        latex_obj = _generate_latex_for_variant(variant, config)
        success = compile_latex_to_pdf(latex_obj, output_base)
        if not success:
            logger.info(f"Errore nella generazione del PDF per la variante {variant.variant_id}")
    logger.info("Generazione dei PDF completata.")

    generate_answer_keys_report(selected_variants, config)
    logger.info("Report delle chiavi di risposta generato su 'answer_keys_report.txt'.")
    logger.info("Mappatura numeri domande -> nomi fogli salvata in 'question_mappings.json'.")

    max_questions = max([len(v.questions) for v in selected_variants]) if selected_variants else 0
    create_student_answers_template(max_questions)
    logger.info("File template 'student_answers.xlsx' creato correttamente (unica scheda).")
    logger.info("\nFase 1 completata: test e template student_answers.xlsx generati.")

def phase2():
    check_files(["student_answers.xlsx", "question_mappings.json"])
    ensure_dir("report_questions")

    config = AppConfig()

    with open("question_mappings.json", "r", encoding="utf-8") as f:
        mappings = json.load(f)
        variant_answer_keys = mappings["variant_answer_keys"]
        variant_question_mappings = mappings["variant_question_mappings"]

    questions_data = load_questions_from_excel("questions.xlsx")
    logger.info(f"Domande caricate da 'questions.xlsx': {len(questions_data)} domande trovate.")

    # We need dummy TestVariants to pass to correct_tests, it only needs questions with correct sheet_name
    # Wait, the variants in correct_tests only uses sheet_name mapping. Let's just create a dummy variant
    # for each variant_id with all questions.
    dummy_variants = []
    for variant_id, mapping in variant_question_mappings.items():
        dummy_variants.append(TestVariant(variant_id=variant_id, questions=questions_data))

    submissions = load_student_answers_from_excel("student_answers.xlsx")
    logger.info("Risposte degli studenti caricate correttamente da student_answers.xlsx")

    test_results, question_analytics = correct_tests(submissions, dummy_variants, variant_answer_keys, variant_question_mappings, config)

    logger.info("Correzione dei test completata. Risultati per studente:")
    for stud, res in test_results.items():
        logger.info(f"Studente {stud}: {res['total_score']} su {res['max_possible_score']} ({res['percentage']}%)")

    analysis_results = analyze_results(test_results, config.passing_threshold)
    logger.info("Analisi dei risultati completata.")
    if analysis_results:
        logger.info(f"Punteggio medio: {analysis_results.get('average_score', 0)}")
        logger.info(f"Deviazione standard: {analysis_results.get('std_deviation', 0)}")
        logger.info(f"Percentuale di promossi: {analysis_results.get('pass_rate', 0)}%")

    question_analytics = analyze_questions(test_results, question_analytics)
    logger.info("Analisi delle domande completata.")

    generate_question_report(question_analytics, analysis_results)
    logger.info("Report delle domande generato correttamente.")

    generate_student_report(test_results, analysis_results)
    logger.info("Report degli studenti generato correttamente.")

    generate_student_reports(test_results)
    generate_student_excel_report(test_results)
    logger.info("Report Excel degli studenti generato correttamente.")
    logger.info("Report consolidato degli studenti generato correttamente.")

    generate_teacher_report(analysis_results, variant_answer_keys, variant_question_mappings)
    logger.info("Report sintetico per l'insegnante generato su 'teacher_report.txt'.")

    logger.info("\nFase 2 completata: correzione test e creazione dei report eseguite con successo!")

def main():
    parser = argparse.ArgumentParser(description="Script per generare test e correggere i test in due fasi.")
    parser.add_argument("--phase", type=int, required=True, choices=[1, 2],
                        help="Fase: 1 per generazione test e template student_answers.xlsx, 2 per correzione test e generazione report")
    args = parser.parse_args()

    if args.phase == 1:
        try:
            phase1()
        except Exception as e:
            logger.info(f"\nErrore in fase 1: {str(e)}")
    elif args.phase == 2:
        try:
            phase2()
        except Exception as e:
            logger.info(f"\nErrore in fase 2: {str(e)}")

if __name__ == "__main__":
    main()
