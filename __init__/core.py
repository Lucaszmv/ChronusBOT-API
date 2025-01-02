"""
Inicialização do módulo core.
"""

import sys
import os
from colorama import Fore, Style, init

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

if __name__ == "__main__":
    print(Fore.YELLOW + "\n✅ Módulo core inicializado com sucesso" + Style.RESET_ALL) 