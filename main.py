"""
Auto Key Clicker - Multi-Monitor Game Clicker
Ponto de entrada principal da aplicação.
"""
import sys
import os

# Adiciona o diretório atual ao path de execução
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui import main

if __name__ == "__main__":
    main()
