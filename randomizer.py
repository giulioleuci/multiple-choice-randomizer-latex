import pandas as pd
import random
import subprocess
import os
import json
import re
from datetime import datetime
import numpy as np
import copy
import argparse
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import scipy.stats as stats
from collections import defaultdict

# Importazioni PyLaTeX
from pylatex import Document, NoEscape, Package
from pylatex.base_classes import Environment

class Multicols(Environment):
    def __init__(self, columns):
        super().__init__('multicols', arguments=[str(columns)])

class TestGeneratorAnalyzer:
    """
    Sistema per la generazione e analisi di test con la classe exam.
    Per ogni scheda del file Excel viene selezionata una sola riga valida.
    Nei file di risposte e nei report le colonne saranno nominate con i numeri delle domande.
    """

    def __init__(self, config_file="config.json"):
        self.config = self._load_config(config_file)
        self.questions_data = []  # Domande, una per ogni foglio
        self.original_questions_order = []
        self.variants = []  # Varianti del test (ovvero, diverse permutazioni delle domande)
        self.variant_answer_keys = {}  # Per ogni variante: dizionario {numero_domanda: lettera}
        self.variant_question_mappings = {}  # Per ogni variante: dizionario {numero_domanda: sheet_name}
        self.student_responses = None
        self.test_results = {}
        self.analysis_results = {}

        # Valori di default per i punteggi (sovrascritti da config.json)
        self.default_correct_score = 4
        self.default_wrong_score = 0
        self.default_no_answer_score = 1
        self.passing_threshold = 0.58

        # Metriche di analisi per le domande
        self.question_analytics = {}
        # Metriche di analisi dettagliate per gli studenti
        self.student_analytics = {}

    def _load_config(self, config_file):
        """Carica la configurazione da JSON (rimuovendo eventuali commenti in stile C)."""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
            config = json.loads(content)

            # Carica i valori di default per i punteggi
            self.default_correct_score = config.get("default_correct_score", 4)
            self.default_wrong_score = config.get("default_wrong_score", 0)
            self.default_no_answer_score = config.get("default_no_answer_score", 1)
            self.passing_threshold = config.get("passing_threshold", 0.58)

            return config
        except FileNotFoundError:
            raise FileNotFoundError(f"File di configurazione non trovato: {config_file}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Errore nella lettura del JSON: {str(e)}")

    def _setup_latex_document(self):
        doc = Document(documentclass="exam")

        # Configurazione geometry
        geom_opts = self.config.get("geometry_options", "top=1cm,bottom=0.5cm,left=1cm,right=1cm")
        doc.packages.append(Package('geometry', options=geom_opts))

        # Aggiungi i pacchetti necessari
        doc.packages.append(Package('multicol'))
        doc.packages.append(Package('enumitem'))
        doc.packages.append(Package('fancyhdr'))
        doc.packages.append(Package('graphicx'))
        doc.packages.append(Package('amsmath'))
        doc.packages.append(Package('amssymb'))
        doc.packages.append(Package('fancybox'))
        doc.packages.append(Package("siunitx"))

        # Configurazione avanzata per l'ambiente delle domande per evitare sovrapposizioni
        doc.preamble.append(NoEscape(r"\renewcommand{\questionlabel}{\thequestion.\hspace{0.5em}}"))
        doc.preamble.append(NoEscape(r"\renewcommand{\choicelabel}{(\alph{choice})\hspace{0.3em}}"))

        # Definizione del comando \um
        doc.preamble.append(NoEscape(r"\newcommand{\um}[2]{\SI[output-decimal-marker={,}]{#1}{#2}}"))

        # Impostazione header e footer
        header_left = self.config.get("firstpageheader_left", "")
        header_center = self.config.get("firstpageheader_center", self.config.get("test_header", ""))
        header_right = self.config.get("firstpageheader_right", "")
        doc.preamble.append(NoEscape(r"\firstpageheader{" + header_left + "}{" + header_center + "}{" + header_right + "}"))

        # Modifica footer per includere numero di variante e numero di pagina
        doc.preamble.append(NoEscape(r"\runningfooter{}{}{Variante~\thevariant~/~\thepage}"))

        # Definizione del contatore per la variante
        doc.preamble.append(NoEscape(r"\newcounter{variant}"))

        return doc

    def _append_student_info_and_answer_grid(self, doc, num_questions, variant_id):
        """
        Aggiunge la riga per le informazioni dello studente e la griglia di risposta.
        La griglia avrà più righe con un numero ottimale di colonne per domanda.
        Include il numero della variante nella intestazione della griglia.
        """
        # Riga per informazioni studente
        doc.append(NoEscape(r"\noindent \textbf{\makebox[0.60\textwidth]{Nome e cognome:\enspace\hrulefill} \makebox[0.15\textwidth]{ Classe:\enspace\hrulefill} \makebox[0.20\textwidth]{ Data:\enspace\hrulefill}}"))

        # Calcola il numero ottimale di colonne per riga
        cols_per_row = min(10, num_questions)  # Max 10 colonne per riga, o meno se ci sono meno domande
        num_rows = (num_questions + cols_per_row - 1) // cols_per_row  # Arrotonda per eccesso

        doc.append(NoEscape(r"\bigskip"))
        doc.append(NoEscape(r"\noindent\textbf{Griglia Risposte (variante " + variant_id + ")}"))

        # Costruisce la griglia multi-riga
        for row in range(num_rows):
            start_q = row * cols_per_row
            end_q = min((row + 1) * cols_per_row, num_questions)
            num_cols_in_row = end_q - start_q

            # Tabella per questa riga
            grid = r"\begin{center}" + "\n" + r"\begin{tabular}{|" + "c|" * num_cols_in_row + "}" + "\n\\hline" + "\n"

            # Riga con i numeri delle domande
            numbers = " & ".join([str(i+1) for i in range(start_q, end_q)])
            grid += numbers + r" \\ \hline" + "\n"

            # Riga con celle vuote per le risposte (più alte per facilitare la scrittura)
            cells = " & ".join([r"\rule{1cm}{0pt}\rule[-0.5em]{0pt}{1.5em}" for _ in range(num_cols_in_row)])
            grid += cells + r" \\ \hline" + "\n" + r"\end{tabular}" + "\n" + r"\end{center}"

            doc.append(NoEscape(grid))

            # Piccolo spazio tra le righe della griglia
            if row < num_rows - 1:
                doc.append(NoEscape(r"\vspace{0.3em}"))

    def _generate_latex_for_variant(self, variant_data):
        """
        Genera un documento LaTeX per una variante del test.
        Per ogni domanda, emette il comando \question con il testo preso così com'è.
        Se sono presenti risposte, viene creato l'ambiente choices con il numero di colonne specificato.
        Prima dell'inizio delle domande, aggiunge le informazioni studente e la griglia di risposta.
        """
        doc = self._setup_latex_document()
        variant_id = variant_data.get('variant_id', 'X')

        # Imposta il contatore della variante
        doc.append(NoEscape(r"\setcounter{variant}{" + variant_id + "}"))

        # Aggiungiamo informazioni studente e griglia risposte in cima al documento, dopo il titolo
        num_questions = len(variant_data.get("questions", []))
        self._append_student_info_and_answer_grid(doc, num_questions, variant_id)

        # Aggiungiamo un po' di spazio prima delle domande
        doc.append(NoEscape(r"\vspace{1em}"))

        # Iniziamo con l'ambiente delle domande
        doc.append(NoEscape(r"\begin{questions}"))
        for question in variant_data.get("questions", []):
            # Aggiungiamo spazio extra attorno al numero della domanda per evitare sovrapposizioni
            qcmd = r"\question " + question["question_text"]
            doc.append(NoEscape(qcmd))
            # Piccolo spazio aggiuntivo dopo il numero della domanda
            doc.append(NoEscape(r"\vspace{0.2em}"))
            answers = question.get("answers", [])
            if answers:
                # Utilizziamo il numero di colonne specificato per le alternative
                num_cols_alternatives = question.get("num_columns_alternatives", 1)

                # Se il numero di colonne è maggiore di 1, utilizziamo multicols
                if num_cols_alternatives > 1:
                    container = doc.create(Multicols(num_cols_alternatives))
                else:
                    container = doc

                container.append(NoEscape(r"\begin{choices}"))
                for ans in answers:
                    container.append(NoEscape(r"\choice " + ans["text"]))
                container.append(NoEscape(r"\end{choices}"))
        doc.append(NoEscape(r"\end{questions}"))

        return doc

    def compile_latex_to_pdf(self, latex_obj, output_filename_base):
        """
        Compila l'oggetto PyLaTeX in PDF.
        Salva il file .tex in "tests_tex" e il PDF in "tests_pdf".
        Se il PDF viene creato (anche con warning), la compilazione è considerata riuscita.
        """
        tex_filename = f"{output_filename_base}.tex"
        pdf_filename = f"{os.path.basename(output_filename_base)}.pdf"
        try:
            latex_obj.generate_tex(output_filename_base)
            for _ in range(2):
                subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", f"-output-directory=tests_pdf", tex_filename],
                    capture_output=True,
                    text=True
                )
            pdf_path = os.path.join("tests_pdf", pdf_filename)
            if os.path.exists(pdf_path):
                return True
            else:
                print(f"Errore nella generazione del PDF per la variante {os.path.basename(output_filename_base)}")
                return False
        except Exception as e:
            print(f"Errore imprevisto: {str(e)}")
            return False
        finally:
            self._cleanup_latex_files(output_filename_base)

    def _cleanup_latex_files(self, base_filename):
        """Elimina i file temporanei generati da LaTeX."""
        extensions = ['.aux', '.log', '.out', '.toc', '.fls', '.fdb_latexmk']
        for ext in extensions:
            temp_file = f"{base_filename}{ext}"
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    print(f"Impossibile rimuovere il file temporaneo: {temp_file}")

    def load_questions_from_excel(self, filename):
        """
        Per ogni scheda (foglio) del file Excel, seleziona una sola riga valida (dove sono presenti
        "Testo della domanda" e "Risposta corretta") e la usa per creare una domanda.
        Il nome della scheda viene salvato (ma non aggiunto al testo nel PDF).
        """
        try:
            xls = pd.ExcelFile(filename)
            self.questions_data = []
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name)
                valid_df = df[df["Testo della domanda"].notna() & df["Risposta corretta"].notna()]
                valid_df = valid_df[valid_df["Testo della domanda"].astype(str).str.strip() != ""]
                valid_df = valid_df[valid_df["Risposta corretta"].astype(str).str.strip() != ""]
                if valid_df.empty:
                    print(f"Foglio '{sheet_name}': nessuna riga valida trovata.")
                    continue
                selected_row = valid_df.sample(n=1).iloc[0]
                question_text = str(selected_row["Testo della domanda"]).strip()
                correct_answer_text = str(selected_row["Risposta corretta"]).strip()
                distractors = []
                for col in df.columns:
                    if col.lower().startswith("alternativa"):
                        val = selected_row.get(col, "")
                        if pd.notnull(val):
                            alt_text = str(val).strip()
                            if alt_text and (alt_text != correct_answer_text):
                                distractors.append(alt_text)
                answers = [{"text": correct_answer_text, "is_correct": True}]
                for dist in distractors:
                    answers.append({"text": dist, "is_correct": False})
                num_cols_altern = 1
                if "Numero Colonne Alternative" in df.columns:
                    val_num = selected_row.get("Numero Colonne Alternative", 1)
                    try:
                        num_cols_altern = int(val_num)
                    except Exception:
                        num_cols_altern = 1

                # Carica i punteggi specifici per questa domanda (o usa i default)
                punteggio_corretta = None
                punteggio_errata = None
                punteggio_non_data = None

                if "Punteggio corretta" in df.columns:
                    val = selected_row.get("Punteggio corretta")
                    if pd.notnull(val):
                        try:
                            punteggio_corretta = float(val)
                        except (ValueError, TypeError):
                            pass

                if "Punteggio errata" in df.columns:
                    val = selected_row.get("Punteggio errata")
                    if pd.notnull(val):
                        try:
                            punteggio_errata = float(val)
                        except (ValueError, TypeError):
                            pass

                if "Punteggio non data" in df.columns:
                    val = selected_row.get("Punteggio non data")
                    if pd.notnull(val):
                        try:
                            punteggio_non_data = float(val)
                        except (ValueError, TypeError):
                            pass

                question = {
                    "question_text": question_text,
                    "sheet_name": sheet_name,
                    "num_columns_alternatives": num_cols_altern,
                    "answers": answers,
                    "punteggio_corretta": punteggio_corretta,
                    "punteggio_errata": punteggio_errata,
                    "punteggio_non_data": punteggio_non_data
                }
                self.questions_data.append(question)
            self.original_questions_order = [q["question_text"] for q in self.questions_data]
            print(f"Domande caricate da '{filename}': {len(self.questions_data)} domande trovate.")
        except Exception as e:
            print(f"Errore nel caricamento delle domande: {str(e)}")

    def generate_test_variants(self, num_variants):
        """
        Genera num_variants varianti del test randomizzando l'ordine delle domande (da fogli diversi)
        e l'ordine delle risposte in ciascuna domanda.
        """
        if not self.questions_data:
            print("Nessuna domanda caricata.")
            return []
        variants = []
        for i in range(num_variants):
            variant_questions = copy.deepcopy(self.questions_data)
            random.shuffle(variant_questions)
            for question in variant_questions:
                random.shuffle(question["answers"])
            variant = {
                "variant_id": str(i + 1),
                "questions": variant_questions
            }
            variants.append(variant)
        print(f"{num_variants} varianti generate.")
        return variants

    def evaluate_randomness_of_variants(self, variants):
        """
        Calcola le metriche di randomicità:
         - question_order_randomness: frazione media di domande in ordine diverso rispetto all'originale.
         - answer_order_randomness: variabilità normalizzata della posizione della risposta corretta.
        Ritorna un dizionario con le metriche.
        """
        if not variants or not self.original_questions_order:
            return {"question_order_randomness": 0, "answer_order_randomness": 0, "combined_randomness": 0}
        num_questions = len(self.original_questions_order)
        question_order_scores = []
        for variant in variants:
            variant_order = [q["question_text"] for q in variant["questions"]]
            diff_count = sum(1 for orig, var in zip(self.original_questions_order, variant_order) if orig != var)
            question_order_scores.append(diff_count / num_questions)
        question_order_randomness = np.mean(question_order_scores)
        answer_positions = {}
        for variant in variants:
            for question in variant["questions"]:
                q_text = question["question_text"]
                correct_index = next((i for i, ans in enumerate(question["answers"]) if ans.get("is_correct", False)), 0)
                if q_text not in answer_positions:
                    answer_positions[q_text] = []
                answer_positions[q_text].append(correct_index)
        normalized_stds = []
        for q_text, positions in answer_positions.items():
            arr = np.array(positions)
            if len(arr) > 1 and (max(arr) - min(arr)) > 0:
                std = np.std(arr)
                n_alternatives = next((len(q["answers"]) for variant in variants for q in variant["questions"] if q["question_text"] == q_text), 1)
                norm_std = std / (n_alternatives - 1) if n_alternatives > 1 else 0
                normalized_stds.append(norm_std)
            else:
                normalized_stds.append(0)
        answer_order_randomness = np.mean(normalized_stds) if normalized_stds else 0
        combined_randomness = (question_order_randomness + answer_order_randomness) / 2
        metrics = {
            "question_order_randomness": round(question_order_randomness, 2),
            "answer_order_randomness": round(answer_order_randomness, 2),
            "combined_randomness": round(combined_randomness, 2)
        }
        print("Metriche di randomicità calcolate:", metrics)
        return metrics

    def select_best_variants(self, potential_variants, randomness_metrics, num_variants):
        """
        Seleziona le migliori varianti in base a uno score (media di question_order_score e answer_order_score).
        """
        scores = []
        for variant in potential_variants:
            variant_order = [q["question_text"] for q in variant["questions"]]
            diff_count = sum(1 for orig, var in zip(self.original_questions_order, variant_order) if orig != var)
            question_order_score = diff_count / len(self.original_questions_order)
            answer_scores = []
            for question in variant["questions"]:
                n_alternatives = len(question["answers"])
                correct_index = next((i for i, ans in enumerate(question["answers"]) if ans.get("is_correct", False)), 0)
                score = (correct_index / (n_alternatives - 1)) if n_alternatives > 1 else 0
                answer_scores.append(score)
            answer_order_score = np.mean(answer_scores) if answer_scores else 0
            variant_score = (question_order_score + answer_order_score) / 2
            scores.append((variant_score, variant))
        scores.sort(key=lambda x: x[0], reverse=True)
        selected = [v for score, v in scores[:num_variants]]
        print(f"{num_variants} varianti selezionate sulla base dello score.")
        return selected

    def generate_test_pdfs(self):
        """
        Per ogni variante, genera il documento LaTeX e compila il PDF.
        I file .tex vengono salvati in tests_tex e i PDF in tests_pdf.
        """
        for variant in self.variants:
            output_base = os.path.join("tests_tex", f"test_variant_{variant.get('variant_id', 'X')}")
            latex_obj = self._generate_latex_for_variant(variant)
            success = self.compile_latex_to_pdf(latex_obj, output_base)
            if not success:
                print(f"Errore nella generazione del PDF per la variante {variant.get('variant_id', 'X')}")
        print("Generazione dei PDF completata.")

    def generate_answer_keys_report(self):
        """
        Per ogni variante, genera un report delle chiavi di risposta e la mappatura
        tra numeri di domanda e nomi dei fogli.
        Il report viene salvato in 'answer_keys_report.txt'.
        Memorizza anche i mapping per la fase di correzione.
        """
        label_style = self.config.get('choice_label_format', 'letters_upper')
        report_lines = []

        for variant in self.variants:
            variant_id = variant.get("variant_id", "X")
            key_mapping = {}  # {numero_domanda: lettera}
            question_mapping = {}  # {numero_domanda: sheet_name}

            for q_idx, question in enumerate(variant.get("questions", [])):
                question_num = str(q_idx + 1)  # Numero della domanda (1-based)
                sheet_name = question.get("sheet_name", "Sconosciuta")

                # Salva il mapping tra numero di domanda e nome del foglio
                question_mapping[question_num] = sheet_name

                # Trova l'indice della risposta corretta
                correct_idx = next((i for i, ans in enumerate(question["answers"]) if ans.get("is_correct", False)), 0)

                # Converte l'indice in lettera o numero secondo il formato configurato
                if label_style == "letters_upper":
                    key = chr(ord('A') + correct_idx)
                elif label_style == "letters_lower":
                    key = chr(ord('a') + correct_idx)
                else:
                    key = str(correct_idx + 1)

                # Salva la chiave di risposta per questa domanda
                key_mapping[question_num] = key

            # Memorizza i mapping per questa variante
            self.variant_answer_keys[variant_id] = key_mapping
            self.variant_question_mappings[variant_id] = question_mapping

            # Genera la linea di report per questa variante
            line = f"Variante {variant_id}: " + " ".join([f"Domanda {qnum}: {key_mapping[qnum]} ({question_mapping[qnum]})" for qnum in sorted(key_mapping.keys(), key=int)])
            report_lines.append(line)

        # Salva il report completo su file
        with open("answer_keys_report.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

        # Salva i mapping in JSON per la fase 2
        mappings_data = {
            "variant_answer_keys": self.variant_answer_keys,
            "variant_question_mappings": self.variant_question_mappings
        }
        with open("question_mappings.json", "w", encoding="utf-8") as f:
            json.dump(mappings_data, f, indent=4)

        print("Report delle chiavi di risposta generato su 'answer_keys_report.txt'.")
        print("Mappatura numeri domande -> nomi fogli salvata in 'question_mappings.json'.")

    def load_student_answers_from_excel(self, filename):
        """
        Carica le risposte degli studenti dal file Excel.
        Il file è organizzato come un'unica scheda con una colonna 'variant_id'
        che specifica il numero della variante per ogni studente.
        Le colonne per le risposte sono numerate con i numeri delle domande (1, 2, 3...).
        """
        try:
            # Carica il file Excel direttamente come un singolo DataFrame
            self.student_responses = pd.read_excel(filename)

            # Verifica che ci siano le colonne essenziali
            required_columns = ["student_id", "variant_id"]
            missing_columns = [col for col in required_columns if col not in self.student_responses.columns]

            if missing_columns:
                raise ValueError(f"Colonne mancanti nel file: {', '.join(missing_columns)}")

            # Converti la colonna variant_id in stringhe per consistenza
            # Converti la colonna variant_id in stringhe senza decimali
            self.student_responses["variant_id"] = self.student_responses["variant_id"].apply(
                lambda x: str(int(float(x))) if pd.notnull(x) and str(x).replace('.','',1).isdigit() else str(x)
            )

            print("Risposte degli studenti caricate correttamente da", filename)
        except Exception as e:
            print(f"Errore nel caricamento delle risposte degli studenti: {str(e)}")

    def correct_tests(self):
        """
        Corregge i test confrontando le risposte degli studenti con le chiavi.
        Utilizza il sistema di punteggio specificato nel file di configurazione e/o nei dati delle domande.
        Le colonne di risposta sono numerate (1, 2, 3...) secondo l'ordine delle domande nel test.
        Le celle vuote sono considerate come risposte non date.
        """
        if self.student_responses is None:
            print("Nessuna risposta studentesca caricata.")
            return

        # Inizializza un dizionario per tenere traccia delle risposte degli studenti per ogni domanda
        # Struttura: {sheet_name: {"correct": count, "wrong": count, "blank": count}}
        question_stats = defaultdict(lambda: {"correct": 0, "wrong": 0, "blank": 0})

        # Per ogni studente
        for index, row in self.student_responses.iterrows():
            student_id = row.get("student_id")
            variant_id = str(row.get("variant_id")).strip()

            if variant_id not in self.variant_answer_keys or variant_id not in self.variant_question_mappings:
                print(f"Attenzione: variante {variant_id} non trovata per lo studente {student_id}.")
                continue

            key_mapping = self.variant_answer_keys[variant_id]  # {numero_domanda: lettera}
            question_mapping = self.variant_question_mappings[variant_id]  # {numero_domanda: sheet_name}

            # Cerca le domande originali per ottenere i punteggi
            # Crea un dizionario {sheet_name: question_data} per un accesso più facile
            question_data_map = {}
            variant_questions = next((v["questions"] for v in self.variants if v["variant_id"] == variant_id), [])
            for q in variant_questions:
                question_data_map[q["sheet_name"]] = q

            # Le colonne di risposta sono quelle diverse da 'student_id' e 'variant_id'
            answer_cols = [col for col in row.index if col not in ["student_id", "variant_id"]]

            # Inizializza i contatori per i diversi tipi di risposte
            correct_count = 0
            wrong_count = 0
            blank_count = 0

            # Inizializza i punteggi
            correct_score = 0
            wrong_score = 0
            blank_score = 0
            max_possible_score = 0

            # Dettaglio delle risposte per questo studente
            student_answers = {}

            for col in answer_cols:
                # Prende la risposta dello studente per questa domanda
                student_ans = str(row.get(col, "")).strip()

                # Verifica se la colonna rappresenta un numero di domanda valido
                if col in key_mapping and col in question_mapping:
                    correct_letter = key_mapping[col]
                    sheet_name = question_mapping[col]

                    # Recupera i dati della domanda per i punteggi personalizzati
                    question_data = question_data_map.get(sheet_name, {})

                    # Determina i punteggi da usare (personalizzati o default)
                    punto_corretta = question_data.get("punteggio_corretta")
                    if punto_corretta is None:
                        punto_corretta = self.default_correct_score

                    punto_errata = question_data.get("punteggio_errata")
                    if punto_errata is None:
                        punto_errata = self.default_wrong_score

                    punto_non_data = question_data.get("punteggio_non_data")
                    if punto_non_data is None:
                        punto_non_data = self.default_no_answer_score

                    # Calcola il punteggio massimo possibile per questa domanda
                    max_possible_score += punto_corretta

                    # Analizza la risposta
                    if pd.isna(row.get(col)) or student_ans == "":  # Risposta non data (cella vuota)
                        blank_count += 1
                        blank_score += punto_non_data
                        student_answers[col] = {"sheet": sheet_name, "response": "blank", "correct": correct_letter, "points": punto_non_data}
                        # Aggiorna le statistiche per questa domanda
                        question_stats[sheet_name]["blank"] += 1
                    elif student_ans.upper() == correct_letter.upper():  # Risposta corretta
                        correct_count += 1
                        correct_score += punto_corretta
                        student_answers[col] = {"sheet": sheet_name, "response": student_ans, "correct": correct_letter, "points": punto_corretta}
                        # Aggiorna le statistiche per questa domanda
                        question_stats[sheet_name]["correct"] += 1
                    else:  # Risposta errata
                        wrong_count += 1
                        wrong_score += punto_errata
                        student_answers[col] = {"sheet": sheet_name, "response": student_ans, "correct": correct_letter, "points": punto_errata}
                        # Aggiorna le statistiche per questa domanda
                        question_stats[sheet_name]["wrong"] += 1

            # Calcola il punteggio totale e la percentuale
            total_score = correct_score + wrong_score + blank_score
            percentage = round((total_score / max_possible_score) * 100, 2) if max_possible_score > 0 else 0

            # Salva i risultati per questo studente
            self.test_results[student_id] = {
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
                "variant_id": variant_id
            }

        # Memorizza le statistiche delle domande per l'analisi successiva
        self.question_analytics = dict(question_stats)

        print("Correzione dei test completata. Risultati per studente:")
        for stud, res in self.test_results.items():
            print(f"Studente {stud}: {res['total_score']} su {res['max_possible_score']} ({res['percentage']}%)")

    def analyze_results(self):
        """
        Calcola statistiche avanzate sui risultati del test.
        """
        if not self.test_results:
            print("Nessun risultato da analizzare.")
            return

        # Statistiche di base
        scores = [res["total_score"] for res in self.test_results.values()]
        percentages = [res["percentage"] for res in self.test_results.values()]
        max_scores = [res["max_possible_score"] for res in self.test_results.values()]

        # Verifica che ci siano dati validi
        if not scores:
            print("Nessun dato valido per l'analisi.")
            return

        # Statistiche descrittive
        avg_score = np.mean(scores)
        med_score = np.median(scores)
        std_dev = np.std(scores)
        min_score = min(scores)
        max_score = max(scores)

        # Percentuale studenti sopra la soglia
        threshold = self.passing_threshold * 100  # Converti in percentuale
        passed = sum(1 for p in percentages if p >= threshold)
        pass_rate = round((passed / len(percentages)) * 100, 2) if percentages else 0

        # Calcola la distribuzione in quartili
        quartiles = np.percentile(scores, [25, 50, 75])

        # Calcola la media dei punteggi per tipo di risposta
        avg_correct = np.mean([res["correct_score"] for res in self.test_results.values()])
        avg_wrong = np.mean([res["wrong_score"] for res in self.test_results.values()])
        avg_blank = np.mean([res["blank_score"] for res in self.test_results.values()])

        # Calcola il numero medio di risposte corrette, errate e non date
        avg_correct_count = np.mean([res["correct_count"] for res in self.test_results.values()])
        avg_wrong_count = np.mean([res["wrong_count"] for res in self.test_results.values()])
        avg_blank_count = np.mean([res["blank_count"] for res in self.test_results.values()])

        # Salva le statistiche di analisi
        self.analysis_results = {
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

        # Calcola metriche aggiuntive per ogni studente
        for student_id, result in self.test_results.items():
            # Calcola il z-score per vedere quanto si discosta dalla media
            z_score = (result["total_score"] - avg_score) / std_dev if std_dev != 0 else 0

            # Calcola il percentile
            percentile = stats.percentileofscore(scores, result["total_score"])

            # Calcola il punteggio stanine (dividendo i punteggi in 9 gruppi)
            # "S+, S, A, B, C, D, E, F, F-"
            stanine_boundaries = np.percentile(scores, [4, 11, 23, 40, 60, 77, 89, 96])
            if result["total_score"] < stanine_boundaries[0]:
                stanine = "F-"
            elif result["total_score"] < stanine_boundaries[1]:
                stanine = "F"
            elif result["total_score"] < stanine_boundaries[2]:
                stanine = "E"
            elif result["total_score"] < stanine_boundaries[3]:
                stanine = "D"
            elif result["total_score"] < stanine_boundaries[4]:
                stanine = "C"
            elif result["total_score"] < stanine_boundaries[5]:
                stanine = "B"
            elif result["total_score"] < stanine_boundaries[6]:
                stanine = "A"
            elif result["total_score"] < stanine_boundaries[7]:
                stanine = "S"
            else:
                stanine = "S+"

            # Aggiungi queste metriche ai risultati dello studente
            self.test_results[student_id].update({
                "z_score": round(z_score, 2),
                "percentile": round(percentile, 2),
                "stanine": stanine
            })

        print("Analisi dei risultati completata.")
        print(f"Punteggio medio: {self.analysis_results['average_score']}")
        print(f"Deviazione standard: {self.analysis_results['std_deviation']}")
        print(f"Percentuale di promossi: {self.analysis_results['pass_rate']}%")

    def analyze_questions(self):
        """
        Calcola metriche avanzate per l'analisi delle domande.
        """
        if not self.question_analytics:
            print("Nessuna statistica delle domande da analizzare.")
            return

        # Per ogni domanda, calcola statistiche aggiuntive
        for sheet_name, stats in self.question_analytics.items():
            total_answers = stats["correct"] + stats["wrong"] + stats["blank"]
            if total_answers == 0:
                continue

            # Percentuali di risposte
            correct_pct = round((stats["correct"] / total_answers) * 100, 2)
            wrong_pct = round((stats["wrong"] / total_answers) * 100, 2)
            blank_pct = round((stats["blank"] / total_answers) * 100, 2)

            # Indice di difficoltà (più alto = più difficile)
            difficulty = 1.0 - (stats["correct"] / total_answers)

            # Indice di discriminazione (correlazione tra risposte corrette a questa domanda e punteggio totale)
            # Dividi gli studenti in gruppi alto/basso in base al punteggio totale
            student_scores = [(student_id, result) for student_id, result in self.test_results.items()]
            student_scores.sort(key=lambda x: x[1]["total_score"], reverse=True)

            # Prendi il 27% superiore e inferiore
            n = len(student_scores)
            upper_n = max(1, int(n * 0.27))
            lower_n = max(1, int(n * 0.27))

            upper_group = student_scores[:upper_n]
            lower_group = student_scores[-lower_n:]

            # Conta quanti in ogni gruppo hanno risposto correttamente a questa domanda
            upper_correct = 0
            lower_correct = 0

            for student_id, result in upper_group:
                for q_num, ans_data in result["answers"].items():
                    if ans_data["sheet"] == sheet_name and ans_data["response"] != "blank" and ans_data["response"].upper() == ans_data["correct"].upper():
                        upper_correct += 1
                        break

            for student_id, result in lower_group:
                for q_num, ans_data in result["answers"].items():
                    if ans_data["sheet"] == sheet_name and ans_data["response"] != "blank" and ans_data["response"].upper() == ans_data["correct"].upper():
                        lower_correct += 1
                        break

            # Calcola l'indice di discriminazione
            p_upper = upper_correct / upper_n if upper_n > 0 else 0
            p_lower = lower_correct / lower_n if lower_n > 0 else 0
            discrimination = p_upper - p_lower

            # Aggiorna le statistiche della domanda
            self.question_analytics[sheet_name].update({
                "total_answers": total_answers,
                "correct_pct": correct_pct,
                "wrong_pct": wrong_pct,
                "blank_pct": blank_pct,
                "difficulty": round(difficulty, 2),
                "discrimination": round(discrimination, 2)
            })

        print("Analisi delle domande completata.")

    def generate_question_report(self):
        """
        Genera un rapporto dettagliato sulle domande del test.
        Crea anche visualizzazioni.
        """
        if not self.question_analytics:
            print("Nessuna statistica delle domande disponibile per il report.")
            return

        # Crea la cartella per i report e le visualizzazioni, se non esiste
        os.makedirs("report_questions", exist_ok=True)

        # Prepara le linee di testo per il report
        lines = ["=== Report delle Domande ===\n"]

        # Aggiungi informazioni generali
        lines.append(f"Numero totale di domande: {len(self.question_analytics)}")
        lines.append(f"Numero totale di studenti: {self.analysis_results.get('num_students', 0)}")
        lines.append(f"Punteggio medio del test: {self.analysis_results.get('average_score', 0)}\n")

        # Aggiungi dettagli per ogni domanda
        lines.append("Dettaglio per Domanda:")

        # Dati per il grafico complessivo
        all_questions_data = {"domande": [], "correct": [], "blank": [], "wrong": []}

        for sheet_name, stats in sorted(self.question_analytics.items()):
            lines.append(f"\n== Domanda: {sheet_name} ==")
            lines.append(f"Risposte corrette: {stats['correct']} ({stats.get('correct_pct', 0)}%)")
            lines.append(f"Risposte errate: {stats['wrong']} ({stats.get('wrong_pct', 0)}%)")
            lines.append(f"Risposte non date: {stats['blank']} ({stats.get('blank_pct', 0)}%)")
            lines.append(f"Indice di difficoltà: {stats.get('difficulty', 0)} (0=facile, 1=difficile)")
            lines.append(f"Indice di discriminazione: {stats.get('discrimination', 0)} (-1=negativo, 1=positivo)")

            # Classifica la domanda in base agli indici
            difficulty_rating = ""
            if stats.get('difficulty', 0) < 0.3:
                difficulty_rating = "Facile"
            elif stats.get('difficulty', 0) < 0.7:
                difficulty_rating = "Media"
            else:
                difficulty_rating = "Difficile"

            discrimination_rating = ""
            disc = stats.get('discrimination', 0)
            if disc < 0:
                discrimination_rating = "Negativa (problematica)"
            elif disc < 0.2:
                discrimination_rating = "Scarsa"
            elif disc < 0.4:
                discrimination_rating = "Buona"
            else:
                discrimination_rating = "Eccellente"

            lines.append(f"Valutazione difficoltà: {difficulty_rating}")
            lines.append(f"Valutazione discriminazione: {discrimination_rating}")

            # Crea un grafico a torta per questa domanda
            self._create_question_pie_chart(sheet_name, stats)

            # Raccoglie dati per il grafico complessivo
            all_questions_data["domande"].append(sheet_name)
            all_questions_data["correct"].append(stats.get('correct_pct', 0))
            all_questions_data["blank"].append(stats.get('blank_pct', 0))
            all_questions_data["wrong"].append(stats.get('wrong_pct', 0))

        # Crea il grafico stacked bar per tutte le domande
        self._create_stacked_bar_chart(all_questions_data)

        # Salva il report su file
        with open(os.path.join("report_questions", "report_quest.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print("Report delle domande generato correttamente.")

    def _create_question_pie_chart(self, sheet_name, stats):
        """
        Crea un grafico a torta per una singola domanda.
        """
        plt.figure(figsize=(8, 6))

        # Dati per il grafico
        labels = ['Corrette', 'Errate', 'Non Date']
        sizes = [stats.get('correct_pct', 0), stats.get('wrong_pct', 0), stats.get('blank_pct', 0)]
        colors = ['green', 'red', 'gray']
        explode = (0.1, 0, 0)  # Evidenzia le risposte corrette

        plt.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%', shadow=True, startangle=140)
        plt.axis('equal')  # Cerchio invece di ellisse

        plt.title(f'Distribuzione Risposte - Domanda: {sheet_name}')

        # Salva il grafico
        safe_name = re.sub(r'[\\/*?:"<>|]', "", sheet_name)  # Rimuove caratteri non validi per i nomi dei file
        plt.savefig(os.path.join("report_questions", f"question_{safe_name}.png"), dpi=300, bbox_inches='tight')
        plt.close()

    def _create_stacked_bar_chart(self, data):
        """
        Crea un grafico a barre impilate per tutte le domande.
        """
        plt.figure(figsize=(12, 8))

        domande = data["domande"]
        corrette = np.array(data["correct"])
        non_date = np.array(data["blank"])
        errate = np.array(data["wrong"])

        # Crea il grafico a barre impilate
        bar_width = 0.8

        # Normalizza i dati se non sono già in percentuale
        if corrette.sum() + non_date.sum() + errate.sum() > 100 * len(domande):
            total = corrette + non_date + errate
            corrette = (corrette / total) * 100
            non_date = (non_date / total) * 100
            errate = (errate / total) * 100

        # Indici delle barre
        indices = np.arange(len(domande))

        # Crea le barre
        plt.bar(indices, corrette, bar_width, color='green', label='Corrette')
        plt.bar(indices, non_date, bar_width, bottom=corrette, color='gray', label='Non Date')
        plt.bar(indices, errate, bar_width, bottom=corrette+non_date, color='red', label='Errate')

        # Aggiungi etichette e titolo
        plt.xlabel('Domande')
        plt.ylabel('Percentuale (%)')
        plt.title('Distribuzione Risposte per Domanda')
        plt.xticks(indices, domande, rotation=45, ha='right')
        plt.legend()

        plt.tight_layout()

        # Salva il grafico
        plt.savefig(os.path.join("report_questions", "all_questions_stacked.png"), dpi=300, bbox_inches='tight')
        plt.close()

    def generate_student_report(self):
        """
        Genera un report dettagliato sugli studenti.
        """
        if not self.test_results:
            print("Nessun risultato disponibile per il report degli studenti.")
            return

        # Prepara le linee di testo per il report
        lines = ["=== Report degli Studenti ===\n"]

        # Aggiungi statistiche generali
        lines.append("Statistiche Generali:")
        lines.append(f"Numero di studenti: {self.analysis_results.get('num_students', 0)}")
        lines.append(f"Punteggio medio: {self.analysis_results.get('average_score', 0)}")
        lines.append(f"Punteggio mediano: {self.analysis_results.get('median_score', 0)}")
        lines.append(f"Deviazione standard: {self.analysis_results.get('std_deviation', 0)}")
        lines.append(f"Punteggio minimo: {self.analysis_results.get('min_score', 0)}")
        lines.append(f"Punteggio massimo: {self.analysis_results.get('max_score', 0)}")
        lines.append(f"Quartili (25%, 50%, 75%): {self.analysis_results.get('quartiles', [0, 0, 0])}")
        lines.append(f"Soglia di sufficienza: {self.analysis_results.get('passing_threshold', 0)}%")
        lines.append(f"Percentuale di promossi: {self.analysis_results.get('pass_rate', 0)}%")
        lines.append(f"Media risposte corrette: {self.analysis_results.get('avg_correct_count', 0)}")
        lines.append(f"Media risposte errate: {self.analysis_results.get('avg_wrong_count', 0)}")
        lines.append(f"Media risposte non date: {self.analysis_results.get('avg_blank_count', 0)}")
        lines.append(f"Media punti risposte corrette: {self.analysis_results.get('avg_correct_score', 0)}")
        lines.append(f"Media punti risposte errate: {self.analysis_results.get('avg_wrong_score', 0)}")
        lines.append(f"Media punti risposte non date: {self.analysis_results.get('avg_blank_score', 0)}\n")

        # Crea un istogramma della distribuzione dei punteggi
        self._create_score_distribution_chart()

        # Aggiungi dettagli per ogni studente
        lines.append("\nDettaglio per Studente:")
        lines.append("Student ID | Var | Corr | Err | ND | P.Corr | P.Err | P.ND | Tot | Max | % | %ile | Z | Stanine")
        lines.append("-" * 100)

        # Converti i risultati in un DataFrame per una facile ordinazione
        results_df = pd.DataFrame.from_dict(self.test_results, orient='index')
        results_df = results_df.sort_values(by='total_score', ascending=False)

        for student_id, row in results_df.iterrows():
            variant = row['variant_id']
            corr_count = row['correct_count']
            wrong_count = row['wrong_count']
            blank_count = row['blank_count']
            corr_score = row['correct_score']
            wrong_score = row['wrong_score']
            blank_score = row['blank_score']
            tot_score = row['total_score']
            max_score = row['max_possible_score']
            percentage = row['percentage']
            percentile = row.get('percentile', 0)
            z_score = row.get('z_score', 0)
            stanine = row.get('stanine', '')

            line = f"{student_id} | {variant} | {corr_count} | {wrong_count} | {blank_count} | "
            line += f"{corr_score} | {wrong_score} | {blank_score} | {tot_score} | {max_score} | "
            line += f"{percentage}% | {percentile} | {z_score} | {stanine}"

            lines.append(line)

        # Salva il report su file
        with open("report_students.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print("Report degli studenti generato correttamente.")

    def _create_score_distribution_chart(self):
        """
        Crea un istogramma della distribuzione dei punteggi.
        """
        scores = [res["total_score"] for res in self.test_results.values()]

        plt.figure(figsize=(10, 6))

        plt.hist(scores, bins=10, color='skyblue', edgecolor='black', alpha=0.7)

        # Aggiungi linee verticali per le statistiche chiave
        plt.axvline(self.analysis_results.get('average_score', 0), color='red', linestyle='--', linewidth=2, label='Media')
        plt.axvline(self.analysis_results.get('median_score', 0), color='green', linestyle='-', linewidth=2, label='Mediana')

        # Calcola la soglia di sufficienza sul punteggio massimo medio
        max_scores = [res["max_possible_score"] for res in self.test_results.values()]
        avg_max = np.mean(max_scores)
        pass_threshold = avg_max * (self.analysis_results.get('passing_threshold', 0) / 100)
        plt.axvline(pass_threshold, color='orange', linestyle='-.', linewidth=2, label='Soglia Sufficienza')

        plt.xlabel('Punteggio')
        plt.ylabel('Numero di Studenti')
        plt.title('Distribuzione dei Punteggi')
        plt.legend()

        plt.tight_layout()

        # Assicurati che la cartella report_questions esista
        os.makedirs("report_questions", exist_ok=True)

        # Salva il grafico
        plt.savefig(os.path.join("report_questions", "score_distribution.png"), dpi=300, bbox_inches='tight')
        plt.close()

    def generate_teacher_report(self):
        """
        Genera un report sintetico per l'insegnante con statistiche e dettaglio per variante.
        """
        lines = []
        lines.append("=== Report Sintetico per l'Insegnante ===")
        lines.append(f"Numero di studenti: {self.analysis_results.get('num_students', 0)}")
        lines.append(f"Punteggio medio: {self.analysis_results.get('average_score', 0)}")
        lines.append(f"Mediana: {self.analysis_results.get('median_score', 0)}")
        lines.append(f"Deviazione standard: {self.analysis_results.get('std_deviation', 0)}")
        lines.append(f"Percentuale di promossi: {self.analysis_results.get('pass_rate', 0)}%")

        lines.append("\nDettaglio per variante:")

        for variant_id in self.variant_answer_keys.keys():
            key_mapping = self.variant_answer_keys[variant_id]
            question_mapping = self.variant_question_mappings[variant_id]

            lines.append(f"\nVariante {variant_id}:")
            for q_num in sorted(key_mapping.keys(), key=int):
                sheet_name = question_mapping.get(q_num, "Sconosciuta")
                answer_key = key_mapping.get(q_num, "?")
                lines.append(f"Domanda {q_num}: Risposta {answer_key} (Foglio: {sheet_name})")

        with open("teacher_report.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print("Report sintetico per l'insegnante generato su 'teacher_report.txt'.")

    def generate_student_reports(self):
        """
        Genera un unico report consolidato per tutti gli studenti in 'report_students_detailed.txt'.
        Include dettagli completi per ciascuno studente.
        """
        if not self.test_results:
            print("Nessun risultato disponibile per generare i report degli studenti.")
            return

        # Prepara le linee di testo per il report consolidato
        all_lines = ["=== Report Dettagliato degli Studenti ===\n"]

        # Ordina gli studenti per punteggio totale (decrescente)
        student_ids = sorted(self.test_results.keys(),
                            key=lambda s: self.test_results[s]["total_score"],
                            reverse=True)

        for student_id in student_ids:
            result = self.test_results[student_id]
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

                # Formatta il messaggio in base al tipo di risposta
                if student_response == "blank":
                    status = f"NON DATA (punti: {points})"
                elif student_response.upper() == correct_answer.upper():
                    status = f"CORRETTA (punti: {points})"
                else:
                    status = f"ERRATA - Risposta corretta: {correct_answer} (punti: {points})"

                lines.append(f"Domanda {q_num} ({sheet_name}): Risposta: {student_response} - {status}")

            # Aggiungi le linee di questo studente al report consolidato
            all_lines.extend(lines)

        # Salva il report consolidato su file
        with open("report_students_detailed.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(all_lines))

        # Crea anche il file Excel con il riepilogo
        self.generate_student_excel_report()

        print("Report consolidato degli studenti generato correttamente.")

    def generate_student_excel_report(self):
        """
        Genera un file Excel con il riepilogo dei risultati degli studenti.
        Include le colonne richieste e calcola il valore percentuale*10 arrotondato a multipli di 0.25.
        Aggiunge una colonna 'answers' che mostra per ogni studente le risposte date e quelle corrette.
        """
        if not self.test_results:
            print("Nessun risultato disponibile per generare il report Excel.")
            return

        # Crea un DataFrame vuoto per il report
        columns = [
            "Student ID", "Var", "Corr", "Err", "ND", "P.Corr", "P.Err", "P.ND",
            "Tot", "Max", "%", "%*10 (0.25)", "%ile", "Z", "Stanine", "answers"
        ]
        df_report = pd.DataFrame(columns=columns)

        # Aggiungi i dati di ogni studente
        for student_id, result in self.test_results.items():
            # Calcola il valore % * 10 arrotondato a multipli di 0.25
            percent_x10 = result["percentage"] * 10 / 100  # Prima converto in valore decimale e moltiplico per 10
            rounded_percent = round(percent_x10 * 4) / 4    # Arrotonda a multipli di 0.25

            # Genera la stringa con il formato richiesto per le risposte
            answer_details = result.get("answers", {})
            answer_strings = []

            for q_num in sorted(answer_details.keys(), key=int):
                ans_data = answer_details[q_num]
                student_response = ans_data.get("response", "")
                correct_answer = ans_data.get("correct", "")

                # Formatta la risposta come richiesto
                if student_response == "blank":
                    student_response = "-"  # Rappresenta le risposte non date con un trattino

                answer_strings.append(f"{q_num}: {student_response} (corr: {correct_answer})")

            # Unisce tutte le risposte in una singola stringa separata da virgole
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
            df_report = df_report._append(row, ignore_index=True)

        # Ordina il DataFrame in ordine alfabetico per Student ID
        df_report = df_report.sort_values(by=["Student ID"], ascending=True)

        # Salva il DataFrame in un file Excel
        df_report.to_excel("report_students_summary.xlsx", index=False)

        print("Report Excel degli studenti generato correttamente.")

def main():
    parser = argparse.ArgumentParser(description="Script per generare test e correggere i test in due fasi.")
    parser.add_argument("--phase", type=int, required=True, choices=[1, 2],
                        help="Fase: 1 per generazione test e template student_answers.xlsx, 2 per correzione test e generazione report")
    args = parser.parse_args()

    if args.phase == 1:
        try:
            os.makedirs("tests_tex", exist_ok=True)
            os.makedirs("tests_pdf", exist_ok=True)
            generator = TestGeneratorAnalyzer()
            required_files = ["config.json", "questions.xlsx"]
            for file in required_files:
                if not os.path.exists(file):
                    raise FileNotFoundError(f"File richiesto non trovato: {file}")
            try:
                subprocess.run(["pdflatex", "--version"], capture_output=True, check=False)
            except Exception:
                raise RuntimeError("pdflatex non trovato nel sistema")

            # Carica le domande da ogni scheda del file Excel
            generator.load_questions_from_excel("questions.xlsx")

            # Genera varianti randomizzando l'ordine delle domande e delle risposte
            num_potential_variants = generator.config.get('num_potential_variants_for_randomness_check', 10)
            potential_variants = generator.generate_test_variants(num_potential_variants)
            randomness_metrics = generator.evaluate_randomness_of_variants(potential_variants)
            print("\n=== Metriche di Randomicità ===")
            for metric, value in randomness_metrics.items():
                print(f"{metric}: {value}")
            num_variants = generator.config.get('num_variants', 1)
            selected_variants = generator.select_best_variants(potential_variants, randomness_metrics, num_variants)
            generator.variants = selected_variants

            # Genera i PDF dei test e il report delle chiavi di risposta
            generator.generate_test_pdfs()
            generator.generate_answer_keys_report()

            # Crea il template Excel per le risposte con un'unica scheda
            # e colonne numerate secondo l'ordine delle domande nel test (1, 2, 3...)
            # Il numero di colonne è basato sulla variante con più domande
            max_questions = max([len(variant["questions"]) for variant in generator.variants])
            cols = ["student_id", "variant_id"] + [str(i+1) for i in range(max_questions)]

            # Crea un DataFrame vuoto con le colonne necessarie
            df_template = pd.DataFrame(columns=cols)

            # Salva il template in Excel
            with pd.ExcelWriter("student_answers.xlsx") as writer:
                df_template.to_excel(writer, sheet_name="Risposte", index=False)

            print("File template 'student_answers.xlsx' creato correttamente (unica scheda).")
            print("\nFase 1 completata: test e template student_answers.xlsx generati.")
        except Exception as e:
            print(f"\nErrore in fase 1: {str(e)}")

    elif args.phase == 2:
        try:
            generator = TestGeneratorAnalyzer()
            required_files = ["student_answers.xlsx", "question_mappings.json"]
            for file in required_files:
                if not os.path.exists(file):
                    raise FileNotFoundError(f"File richiesto non trovato: {file}")

            # Crea la cartella per i report delle domande, se non esiste
            os.makedirs("report_questions", exist_ok=True)

            # Carica le mappature tra numeri di domanda e nomi dei fogli
            with open("question_mappings.json", "r", encoding="utf-8") as f:
                mappings = json.load(f)
                generator.variant_answer_keys = mappings["variant_answer_keys"]
                generator.variant_question_mappings = mappings["variant_question_mappings"]

            # Carica le domande originali per ottenere i punteggi
            generator.load_questions_from_excel("questions.xlsx")

            # Carica le risposte degli studenti
            generator.load_student_answers_from_excel("student_answers.xlsx")

            # Corregge i test con il nuovo sistema di punteggi
            generator.correct_tests()

            # Analisi avanzata dei risultati
            generator.analyze_results()

            # Analisi delle domande
            generator.analyze_questions()

            # Genera i report avanzati
            generator.generate_question_report()  # Report delle domande
            generator.generate_student_report()   # Report degli studenti

            # Genera il report consolidato degli studenti e il file Excel riepilogativo
            generator.generate_student_reports()

            # Genera il report per l'insegnante
            generator.generate_teacher_report()

            print("\nFase 2 completata: correzione test e creazione dei report eseguite con successo!")
        except Exception as e:
            print(f"\nErrore in fase 2: {str(e)}")

if __name__ == "__main__":
    main()
