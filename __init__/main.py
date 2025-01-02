"""
Inicialização principal do projeto.
"""

from colorama import Fore, Style, init

init()

# Importar inicializações dos submódulos
from __init__.core import *
from __init__.utils import *

if __name__ == "__main__":
    print(Fore.YELLOW + "\n✅ Módulo principal inicializado com sucesso" + Style.RESET_ALL)
    print("=" * 70) 