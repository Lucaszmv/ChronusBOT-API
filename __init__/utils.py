"""
Inicialização do módulo utils.
"""

import sys
import os
from colorama import Fore, Style, init

# Inicializar o colorama
init()

from modules.utils.utils_proxy_manager import (
    ProxyManager,
    create_proxy_manager
)

from modules.utils.utils_segment_download import (
    simular_download_segmento,
    processar_fila_download,
    iniciar_downloader
)

from modules.utils.utils_update_playlist import (
    atualizar_playlist
)

from modules.utils.utils_stream_checker import (
    verificar_canal_online
)

from modules.utils.utils_logger import get_logger, logger_manager
from modules.utils.utils_failure_manager import get_failure_manager, FailureManager

__all__ = [
    'ProxyManager',
    'create_proxy_manager',
    'simular_download_segmento',
    'processar_fila_download',
    'iniciar_downloader',
    'atualizar_playlist',
    'verificar_canal_online',
    'get_logger',
    'logger_manager',
    'get_failure_manager',
    'FailureManager'
]

if __name__ == "__main__":
    print(Fore.YELLOW + "\n✅ Módulo utils inicializado com sucesso" + Style.RESET_ALL) 