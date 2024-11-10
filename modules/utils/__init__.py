"""
Módulo principal do pacote utils.

Este módulo inicializa e expõe as funcionalidades utilitárias do ChronusBOT,
incluindo gerenciamento de proxies, download de segmentos, atualização de playlists
e verificação de status de streams.

Imports:
    utils_proxy_manager: Gerenciamento de proxies para os bots.
    utils_segment_download: Download e processamento de segmentos de stream.
    utils_update_playlist: Atualização e gerenciamento de playlists M3U8.
    twitch_stream_checker: Verificação de status de streams da Twitch.

Exports:
    ProxyManager: Classe para gerenciamento de proxies.
    create_proxy_manager: Factory function para criar instâncias do ProxyManager.
    simular_download_segmento: Simula download de segmentos de stream.
    processar_fila_download: Processa fila de segmentos para download.
    iniciar_downloader: Inicia processamento da fila em thread separada.
    atualizar_playlist: Atualiza playlist M3U8 de um canal.
    verificar_canal_online: Verifica se um canal da Twitch está online.
"""

import sys
import os
from colorama import Fore, Style, init

# Adicionar o diretório raiz do projeto ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

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

from modules.utils.twitch_stream_checker import (
    verificar_canal_online
)

__all__ = [
    'ProxyManager',
    'create_proxy_manager',
    'simular_download_segmento',
    'processar_fila_download',
    'iniciar_downloader',
    'atualizar_playlist',
    'verificar_canal_online'
]

# Testando importações
if __name__ == "__main__":
    print(Fore.YELLOW + "\n✅ Módulo utils inicializado com sucesso" + Style.RESET_ALL)
    print("=" * 70)
    
    # Testando importações do utils_proxy_manager
    print(Fore.CYAN + "\nVerificando utils_proxy_manager:" + Style.RESET_ALL)
    print(f"✓ ProxyManager: {ProxyManager.__name__}")
    print(f"✓ create_proxy_manager: {create_proxy_manager.__name__}")
    
    # Testando importações do utils_segment_download
    print(Fore.CYAN + "\nVerificando utils_segment_download:" + Style.RESET_ALL)
    print(f"✓ simular_download_segmento: {simular_download_segmento.__name__}")
    print(f"✓ processar_fila_download: {processar_fila_download.__name__}")
    print(f"✓ iniciar_downloader: {iniciar_downloader.__name__}")
    
    # Testando importações do utils_update_playlist
    print(Fore.CYAN + "\nVerificando utils_update_playlist:" + Style.RESET_ALL)
    print(f"✓ atualizar_playlist: {atualizar_playlist.__name__}")
    
    # Testando importações do twitch_stream_checker
    print(Fore.CYAN + "\nVerificando twitch_stream_checker:" + Style.RESET_ALL)
    print(f"✓ verificar_canal_online: {verificar_canal_online.__name__}")
    
    print("\n" + "=" * 70)