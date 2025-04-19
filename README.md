# Test Generator Analyzer

Un sistema completo per la generazione, randomizzazione, correzione e analisi di test a risposta multipla con supporto LaTeX. Ideale per docenti e formatori che necessitano di creare varianti diverse di uno stesso test e analizzare in dettaglio i risultati.

## Caratteristiche principali

- **Generazione di test randomizzati**: Crea molteplici versioni dello stesso test con domande e risposte in ordine diverso, e varianti delle domande
- **Output in formato PDF** tramite LaTeX con la classe `exam`
- **Correzione automatizzata** delle risposte degli studenti
- **Analisi avanzata** dei risultati con metriche
- **Report dettagliati** per ogni domanda e per ogni studente
- **Visualizzazioni grafiche** della performance e delle difficoltà delle domande

## Requisiti di sistema

- Python 3.6+
- LaTeX (con la classe `exam` installata)
- Librerie Python (installabili via pip):
  - pandas
  - numpy
  - matplotlib
  - scipy
  - pylatex

## Installazione

1. Clona il repository o scarica i file sorgente
```
git clone https://github.com/tuousername/test-generator-analyzer.git
cd test-generator-analyzer
```

2. Installa le dipendenze Python
```
pip install pandas numpy matplotlib scipy pylatex
```

3. Verifica che LaTeX sia installato correttamente
```
pdflatex --version
```

## Struttura del progetto

Prima di iniziare, assicurati di avere questa struttura di cartelle:

```
test-generator-analyzer/
├── randomizer.py        # Script principale
├── config.json          # File di configurazione
├── questions.xlsx       # File Excel con le domande
├── tests_tex/           # Cartella per i file .tex generati (creata automaticamente)
├── tests_pdf/           # Cartella per i PDF generati (creata automaticamente)
└── report_questions/    # Cartella per i report e grafici (creata automaticamente)
```

## Configurazione

Il file `config.json` contiene i parametri di configurazione:

```json
{
  "default_correct_score": 4,     /* Punteggio per risposte corrette */
  "default_wrong_score": 0,       /* Punteggio per risposte errate */
  "default_no_answer_score": 1,   /* Punteggio per risposte non date */
  "passing_threshold": 0.58,      /* Soglia di sufficienza (58%) */
  "num_variants": 3,              /* Numero di varianti da generare */
  "num_potential_variants_for_randomness_check": 10, /* Varianti potenziali da valutare */
  "geometry_options": "top=1cm,bottom=0.5cm,left=1cm,right=1cm", /* Opzioni LaTeX */
  "test_header": "Test di esempio - Prova",  /* Intestazione del test */
  "firstpageheader_left": "",    /* Contenuto header sinistro */
  "firstpageheader_center": "",  /* Contenuto header centrale */
  "firstpageheader_right": "",   /* Contenuto header destro */
  "choice_label_format": "letters_upper" /* Formato etichette risposte (A, B, C...) */
}
```

## Preparazione del file delle domande

Il file `questions.xlsx` deve contenere:

- Un foglio separato per ogni "gruppo" di domande
- Ogni foglio deve contenere almeno queste colonne:
  - `Testo della domanda`: Il testo della domanda
  - `Risposta corretta`: Il testo della risposta corretta
  - `Alternativa X`: Il desto delle altre possibili risposte (distrattori)
  - Opzionalmente: `Numero Colonne Alternative`, `Punteggio corretta`, `Punteggio errata`, `Punteggio non data`

## Utilizzo

Il programma funziona in due fasi distinte:

### Fase 1: Generazione dei test

```
python randomizer.py --phase 1
```

Questa fase:
1. Carica le domande dal file Excel
2. Genera varianti randomizzate del test
3. Crea i file PDF per ogni variante
4. Genera un report con le chiavi di risposta
5. Crea un template Excel vuoto (`student_answers.xlsx`) per inserire le risposte degli studenti

### Fase 2: Correzione e analisi

Dopo aver compilato il file `student_answers.xlsx` con le risposte degli studenti:

```
python randomizer.py --phase 2
```

Questa fase:
1. Corregge le risposte degli studenti
2. Analizza i risultati con metriche statistiche
3. Genera report dettagliati e visualizzazioni
4. Crea un file Excel riepilogativo con tutti i risultati

## File generati

### Fase 1
- `tests_pdf/test_variant_X.pdf`: PDF delle varianti dei test
- `tests_tex/test_variant_X.tex`: File sorgente LaTeX
- `answer_keys_report.txt`: Report delle chiavi di risposta
- `question_mappings.json`: Mappatura delle domande e risposte
- `student_answers.xlsx`: Template per inserire le risposte

### Fase 2
- `report_quest.txt`: Report dettagliato sulle domande
- `report_students.txt`: Report sintetico sugli studenti
- `report_students_detailed.txt`: Report dettagliato per ogni studente
- `report_students_summary.xlsx`: Riepilogo in formato Excel con tutti i dati
- `teacher_report.txt`: Report sintetico per l'insegnante
- `report_questions/*.png`: Grafici e visualizzazioni

## Analisi dei risultati

Il sistema calcola diverse metriche statistiche, tra cui:

- **Per gli studenti**: punteggio totale, percentuale, z-score, percentile, stanine
- **Per le domande**: indice di difficoltà, indice di discriminazione, percentuale di risposte corrette/errate/non date

### Grafici generati

- Distribuzione dei punteggi (istogramma)
- Grafici a torta per ogni domanda
- Grafico a barre impilate per tutte le domande

## Personalizzazione dei punteggi

È possibile assegnare punteggi diversi per ogni domanda inserendo nel file Excel le colonne:
- `Punteggio corretta`: Punti per risposte corrette
- `Punteggio errata`: Punti per risposte errate
- `Punteggio non data`: Punti per risposte non date

Se non specificati, vengono utilizzati i valori predefiniti dal `config.json`.

## Suggerimenti per l'uso

- Prepara attentamente il file Excel con le domande, assicurandoti che ogni foglio contenga domande dello stesso argomento o difficoltà
- Verifica il file `student_answers.xlsx` prima di eseguire la fase 2
- Controlla i valori di randomizzazione per assicurarti che le varianti siano sufficientemente diverse
- Utilizza i report per migliorare le domande in base agli indici di difficoltà e discriminazione

## Risoluzione problemi

### LaTeX non genera i PDF
- Verifica che LaTeX sia installato e funzionante
- Controlla i log in `tests_tex` per errori specifici
- Assicurati che la classe `exam` sia installata

### Problemi con il file Excel
- Verifica che le colonne siano nominate esattamente come richiesto
- Assicurati che non ci siano celle vuote nelle colonne obbligatorie
- Controlla la formattazione delle celle (testo vs numeri)

### Fase 2 genera errori
- Verifica che il file `student_answers.xlsx` sia formattato correttamente
- Controlla che gli ID delle varianti corrispondano a quelli generati
- Assicurati che tutte le risposte siano in formato valido

## Licenza

Questo progetto è distribuito con licenza GPL. Vedi il file `LICENSE` per i dettagli.

---

*Sviluppato per supportare i docenti nella creazione di test randomizzati e nell'analisi dettagliata dei risultati.*
