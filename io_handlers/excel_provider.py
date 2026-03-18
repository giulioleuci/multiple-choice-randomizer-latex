import pandas as pd
from typing import List, Dict, Any
from core.models import Question, AnswerChoice, StudentSubmission

def _parse_row(selected_row: pd.Series, sheet_name: str, df_columns: List[str]) -> Question:
    question_text = str(selected_row["Testo della domanda"]).strip()
    correct_answer_text = str(selected_row["Risposta corretta"]).strip()
    distractors = []

    for col in df_columns:
        if col.lower().startswith("alternativa"):
            val = selected_row.get(col, "")
            if pd.notnull(val):
                alt_text = str(val).strip()
                if alt_text and (alt_text != correct_answer_text):
                    distractors.append(alt_text)

    answers = [AnswerChoice(text=correct_answer_text, is_correct=True)]
    for dist in distractors:
        answers.append(AnswerChoice(text=dist, is_correct=False))

    num_cols_altern = 1
    if "Numero Colonne Alternative" in df_columns:
        val_num = selected_row.get("Numero Colonne Alternative", 1)
        try:
            num_cols_altern = int(val_num)
        except Exception:
            num_cols_altern = 1

    punteggio_corretta = None
    punteggio_errata = None
    punteggio_non_data = None

    if "Punteggio corretta" in df_columns:
        val = selected_row.get("Punteggio corretta")
        if pd.notnull(val):
            try:
                punteggio_corretta = float(val)
            except (ValueError, TypeError):
                pass

    if "Punteggio errata" in df_columns:
        val = selected_row.get("Punteggio errata")
        if pd.notnull(val):
            try:
                punteggio_errata = float(val)
            except (ValueError, TypeError):
                pass

    if "Punteggio non data" in df_columns:
        val = selected_row.get("Punteggio non data")
        if pd.notnull(val):
            try:
                punteggio_non_data = float(val)
            except (ValueError, TypeError):
                pass

    return Question(
        question_text=question_text,
        sheet_name=sheet_name,
        answers=answers,
        num_columns_alternatives=num_cols_altern,
        punteggio_corretta=punteggio_corretta,
        punteggio_errata=punteggio_errata,
        punteggio_non_data=punteggio_non_data
    )

def load_questions_from_excel(filename: str) -> List[Question]:
    try:
        all_sheets = pd.read_excel(filename, sheet_name=None)
        questions_data = []
        for sheet_name, df in all_sheets.items():
            if "Testo della domanda" not in df.columns or "Risposta corretta" not in df.columns:
                continue
            valid_df = df[df["Testo della domanda"].notna() & df["Risposta corretta"].notna()]
            valid_df = valid_df[valid_df["Testo della domanda"].astype(str).str.strip() != ""]
            valid_df = valid_df[valid_df["Risposta corretta"].astype(str).str.strip() != ""]
            if valid_df.empty:
                continue

            selected_row = valid_df.sample(n=1).iloc[0]
            question = _parse_row(selected_row, sheet_name, df.columns.tolist())
            questions_data.append(question)
        return questions_data
    except Exception as e:
        raise RuntimeError(f"Errore nel caricamento delle domande: {str(e)}")

def load_student_answers_from_excel(filename: str) -> List[StudentSubmission]:
    try:
        df = pd.read_excel(filename)
        required_columns = ["student_id", "variant_id"]
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            raise ValueError(f"Colonne mancanti nel file: {', '.join(missing_columns)}")

        df["variant_id"] = df["variant_id"].apply(
            lambda x: str(int(float(x))) if pd.notnull(x) and str(x).replace('.','',1).isdigit() else str(x)
        )

        submissions = []
        for _, row in df.iterrows():
            student_id = str(row.get("student_id"))
            variant_id = str(row.get("variant_id")).strip()
            answer_cols = [col for col in row.index if col not in ["student_id", "variant_id"]]
            answers = {str(col): str(row.get(col, "")).strip() for col in answer_cols}
            submissions.append(StudentSubmission(student_id=student_id, variant_id=variant_id, answers=answers))

        return submissions
    except Exception as e:
        raise RuntimeError(f"Errore nel caricamento delle risposte degli studenti: {str(e)}")

def create_student_answers_template(max_questions: int, filename: str = "student_answers.xlsx"):
    cols = ["student_id", "variant_id"] + [str(i+1) for i in range(max_questions)]
    df_template = pd.DataFrame(columns=cols)
    with pd.ExcelWriter(filename) as writer:
        df_template.to_excel(writer, sheet_name="Risposte", index=False)

def sanitize_for_excel(value: Any) -> Any:
    if isinstance(value, str) and value:
        triggers = ('=', '+', '-', '@', '\t', '\r')
        stripped = value.lstrip()
        if value[0] in triggers or (stripped and stripped[0] in triggers):
            return "'" + value
    return value

def generate_student_excel_report(test_results: Dict[str, Any], filename: str = "report_students_summary.xlsx"):
    if not test_results:
        return

    rows = []
    columns = [
        "Student ID", "Var", "Corr", "Err", "ND", "P.Corr", "P.Err", "P.ND",
        "Tot", "Max", "%", "%*10 (0.25)", "%ile", "Z", "Stanine", "answers"
    ]

    for student_id, result in test_results.items():
        percent_x10 = result["percentage"] * 10 / 100
        rounded_percent = round(percent_x10 * 4) / 4

        answer_details = result.get("answers", {})
        answer_strings = []

        for q_num in sorted(answer_details.keys(), key=int):
            ans_data = answer_details[q_num]
            student_response = ans_data.get("response", "")
            correct_answer = ans_data.get("correct", "")

            if student_response == "blank":
                student_response = "-"

            answer_strings.append(f"{q_num}: {student_response} (corr: {correct_answer})")

        answers_string = ", ".join(answer_strings)

        row = {
            "Student ID": student_id,
            "Var": result["variant_id"],
            "Corr": result["correct_count"],
            "Err": result["wrong_count"],
            "ND": result["blank_count"],
            "P.Corr": result["correct_score"],
            "P.Err": result["wrong_score"],
            "P.ND": result["blank_score"],
            "Tot": result["total_score"],
            "Max": result["max_possible_score"],
            "%": result["percentage"],
            "%*10 (0.25)": rounded_percent,
            "%ile": result.get("percentile", 0),
            "Z": result.get("z_score", 0),
            "Stanine": result.get("stanine", ""),
            "answers": answers_string
        }
        rows.append(row)

    df_report = pd.DataFrame(rows, columns=columns)
    df_report = df_report.sort_values(by=["Student ID"], ascending=True)

    for col in df_report.select_dtypes(include=['object', 'string']).columns:
        df_report[col] = df_report[col].apply(sanitize_for_excel)

    df_report.to_excel(filename, index=False)
