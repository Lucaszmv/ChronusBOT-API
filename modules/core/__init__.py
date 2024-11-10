"""
Módulo principal do pacote core.

Este módulo inicializa e expõe as principais funcionalidades do pacote core,
incluindo funções para manipulação de tokens, fingerprints e gerenciamento de sessão.

Imports:
    core_token: Funções para manipulação de tokens de acesso.
    core_fingerprint: Funções e constantes para geração de fingerprints.
    core_session: Objeto de sessão HTTP reutilizável.
"""

import sys
import os
from colorama import Fore, Style, init
import urllib3

# Suprime avisos SSL globalmente
urllib3.disable_warnings()

# Adicionar o diretório raiz do projeto ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Inicializar o colorama
init()

from modules.core.core_token import (
    get_playback_access_token_headers,
    criar_payload_playback_token,
    obter_playback_access_token
)

from modules.core.core_fingerprint import (
    CLIENT_ID,
    get_fingerprint
)

from modules.core.core_session import session_manager

__all__ = [
    'get_playback_access_token_headers',
    'criar_payload_playback_token',
    'obter_playback_access_token',
    'CLIENT_ID',
    'get_fingerprint',
    'session_manager'
] 

# Testando importações
if __name__ == "__main__":
    print(Fore.YELLOW + "\n✅ Módulo core inicializado com sucesso" + Style.RESET_ALL)
    print("=" * 70)
    
    # Testando importações do core_fingerprint
    print(Fore.CYAN + "\nVerificando core_fingerprint:" + Style.RESET_ALL)
    print(f"✓ CLIENT_ID: {CLIENT_ID[:10]}...")
    print(f"✓ get_fingerprint: {get_fingerprint()}")
    
    # Testando importações do core_token
    print(Fore.CYAN + "\nVerificando core_token:" + Style.RESET_ALL)
    print(f"✓ get_playback_access_token_headers: {get_playback_access_token_headers.__name__}")
    print(f"✓ criar_payload_playback_token: {criar_payload_playback_token.__name__}")
    print(f"✓ obter_playback_access_token: {obter_playback_access_token.__name__}")
    
    # Testando importações do core_session
    print(Fore.CYAN + "\nVerificando core_session:" + Style.RESET_ALL)
    print(f"✓ session_manager: {session_manager}")
    
    print("\n" + "=" * 70)
