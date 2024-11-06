"""
Módulo principal do pacote core.

Este módulo inicializa e expõe as principais funcionalidades do pacote core,
incluindo funções para manipulação de tokens, fingerprints e gerenciamento de sessão.

Imports:
    core_token: Funções para manipulação de tokens de acesso.
    core_fingerprint: Funções e constantes para geração de fingerprints.
    core_session: Objeto de sessão HTTP reutilizável.

Exports:
    get_playback_access_token_headers: Obtém headers para token de playback.
    criar_payload_playback_token: Cria payload para requisição de token.
    obter_playback_access_token: Obtém token de acesso para playback.
    testar_obter_playback_access_token: Testa obtenção de token de playback.
    CLIENT_ID: ID do cliente para a API da Twitch.
    get_fingerprint: Obtém fingerprint atual ou gera novo.
    session: Objeto de sessão HTTP reutilizável.
"""

import sys
import os
from colorama import Fore, Style, init

# Adicionar o diretório raiz do projeto ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

#inicializar o colorama
init()

from modules.core.core_token import (
    get_playback_access_token_headers,
    criar_payload_playback_token,
    obter_playback_access_token,
    testar_obter_playback_access_token
)

from modules.core.core_fingerprint import (
    CLIENT_ID,
    get_fingerprint
)

from modules.core.core_session import session

__all__ = [
    'get_playback_access_token_headers',
    'criar_payload_playback_token',
    'obter_playback_access_token',
    'testar_obter_playback_access_token',
    'CLIENT_ID',
    'get_fingerprint',
    'session'
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
    print(f"✓ testar_obter_playback_access_token: {testar_obter_playback_access_token.__name__}")
    
    # Testando importações do core_session
    print(Fore.CYAN + "\nVerificando core_session:" + Style.RESET_ALL)
    print(f"✓ session: {session}")
    
    print("\n" + "=" * 70)

