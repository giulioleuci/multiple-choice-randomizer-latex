import os
import subprocess
from pylatex import Document, NoEscape, Package
from pylatex.base_classes import Environment
from core.models import TestVariant
from core.config import AppConfig
from utils.fs_ops import cleanup_latex_files

class Multicols(Environment):
    def __init__(self, columns):
        super().__init__('multicols', arguments=[str(columns)])

def _setup_latex_document(config: AppConfig) -> Document:
    doc = Document(documentclass="exam")
    geom_opts = config.get("geometry_options", "top=1cm,bottom=0.5cm,left=1cm,right=1cm")
    doc.packages.append(Package('geometry', options=geom_opts))
    doc.packages.append(Package('multicol'))
    doc.packages.append(Package('enumitem'))
    doc.packages.append(Package('fancyhdr'))
    doc.packages.append(Package('graphicx'))
    doc.packages.append(Package('amsmath'))
    doc.packages.append(Package('amssymb'))
    doc.packages.append(Package('fancybox'))
    doc.packages.append(Package("siunitx"))

    doc.preamble.append(NoEscape(r"\renewcommand{\questionlabel}{\thequestion.\hspace{0.5em}}"))
    doc.preamble.append(NoEscape(r"\renewcommand{\choicelabel}{(\alph{choice})\hspace{0.3em}}"))
    doc.preamble.append(NoEscape(r"\newcommand{\um}[2]{\SI[output-decimal-marker={,}]{#1}{#2}}"))

    header_left = config.get("firstpageheader_left", "")
    header_center = config.get("firstpageheader_center", config.get("test_header", ""))
    header_right = config.get("firstpageheader_right", "")
    doc.preamble.append(NoEscape(r"\firstpageheader{" + header_left + "}{" + header_center + "}{" + header_right + "}"))
    doc.preamble.append(NoEscape(r"\runningfooter{}{}{Variante~\thevariant~/~\thepage}"))
    doc.preamble.append(NoEscape(r"\newcounter{variant}"))

    return doc

def _append_student_info_and_answer_grid(doc: Document, num_questions: int, variant_id: str):
    doc.append(NoEscape(r"\noindent \textbf{\makebox[0.60\textwidth]{Nome e cognome:\enspace\hrulefill} \makebox[0.15\textwidth]{ Classe:\enspace\hrulefill} \makebox[0.20\textwidth]{ Data:\enspace\hrulefill}}"))

    cols_per_row = min(10, num_questions)
    num_rows = (num_questions + cols_per_row - 1) // cols_per_row

    doc.append(NoEscape(r"\bigskip"))
    doc.append(NoEscape(r"\noindent\textbf{Griglia Risposte (variante " + variant_id + ")}"))

    for row in range(num_rows):
        start_q = row * cols_per_row
        end_q = min((row + 1) * cols_per_row, num_questions)
        num_cols_in_row = end_q - start_q

        grid = r"\begin{center}" + "\n" + r"\begin{tabular}{|" + "c|" * num_cols_in_row + "}" + "\n\\hline" + "\n"
        numbers = " & ".join([str(i+1) for i in range(start_q, end_q)])
        grid += numbers + r" \\ \hline" + "\n"

        cells = " & ".join([r"\rule{1cm}{0pt}\rule[-0.5em]{0pt}{1.5em}" for _ in range(num_cols_in_row)])
        grid += cells + r" \\ \hline" + "\n" + r"\end{tabular}" + "\n" + r"\end{center}"

        doc.append(NoEscape(grid))
        if row < num_rows - 1:
            doc.append(NoEscape(r"\vspace{0.3em}"))

def _generate_latex_for_variant(variant: TestVariant, config: AppConfig) -> Document:
    doc = _setup_latex_document(config)
    variant_id = variant.variant_id

    doc.append(NoEscape(r"\setcounter{variant}{" + variant_id + "}"))
    num_questions = len(variant.questions)
    _append_student_info_and_answer_grid(doc, num_questions, variant_id)

    doc.append(NoEscape(r"\vspace{1em}"))
    doc.append(NoEscape(r"\begin{questions}"))

    for question in variant.questions:
        qcmd = r"\question " + question.question_text
        doc.append(NoEscape(qcmd))
        doc.append(NoEscape(r"\vspace{0.2em}"))
        if question.answers:
            num_cols = question.num_columns_alternatives
            if num_cols > 1:
                doc.append(NoEscape(r"\begin{multicols}{" + str(num_cols) + "}"))
            doc.append(NoEscape(r"\begin{choices}"))
            for ans in question.answers:
                doc.append(NoEscape(r"\choice " + ans.text))
            doc.append(NoEscape(r"\end{choices}"))
            if num_cols > 1:
                doc.append(NoEscape(r"\end{multicols}"))

    doc.append(NoEscape(r"\end{questions}"))
    return doc

def compile_latex_to_pdf(latex_obj: Document, output_filename_base: str) -> bool:
    tex_filename = f"{output_filename_base}.tex"
    pdf_filename = f"{os.path.basename(output_filename_base)}.pdf"
    try:
        latex_obj.generate_tex(output_filename_base)
        for _ in range(2):
            subprocess.run(
                ["pdflatex", "-no-shell-escape", "-interaction=nonstopmode", f"-output-directory=tests_pdf", tex_filename],
                capture_output=True,
                text=True,
                timeout=30
            )
        pdf_path = os.path.join("tests_pdf", pdf_filename)
        return os.path.exists(pdf_path)
    except Exception as e:
        return False
    finally:
        cleanup_latex_files(output_filename_base)
