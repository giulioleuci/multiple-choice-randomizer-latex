import sys
import os

# Aggiungi la root del progetto al path in modo da trovare il modulo main
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import main

if __name__ == "__main__":
    main.main()
