"""
Módulo para atualização e gerenciamento de playlists M3U8 da Twitch.
"""

import random
import time
import logging
from typing import List, Set, Optional
import requests
import os
import sys
from colorama import Fore, Style, init
from pathlib import Path
from datetime import datetime, timezone
from collections import deque
import json
from modules.utils.utils_rate_limiter import get_rate_limiter

# Inicializa o Colorama
init()

# Configurações de cores
INFO_COLOR = Fore.CYAN
SUCCESS_COLOR = Fore.GREEN
WARNING_COLOR = Fore.YELLOW
ERROR_COLOR = Fore.RED
RESET = Style.RESET_ALL
MAGENTA_COLOR = Fore.MAGENTA

# Adiciona o diretório raiz do projeto ao PYTHONPATH
root_dir = str(Path(__file__).parent.parent.parent)
sys.path.append(root_dir)

try:
    # Importações dos módulos core
    from modules.core.core_token import obter_playback_access_token
    from modules.core.core_get_playlist import obter_playlist_m3u8, tentar_obter_playlist_com_retry
    
    # Importações dos módulos utils
    from modules.utils.utils_segment_download import iniciar_downloader
    from modules.utils.utils_ads_detector import create_ad_detector
    from modules.core.core_session import session_manager
except ImportError as e:
    print(f"Erro ao importar módulos: {e}")
    sys.exit(1)

# Configuração do logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Evita duplicação de handlers
if not logger.handlers:
    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


def extrair_links_qualidade(playlist: str) -> List[str]:
    """
    Extrai os links de qualidade da playlist M3U8 principal.

    Args:
        playlist (str): Conteúdo da playlist M3U8 principal.

    Returns:
        List[str]: Lista de URLs das diferentes qualidades disponíveis.
    """
    return [linha for linha in playlist.split('\n') if linha.startswith('https://') and '.m3u8' in linha]

def obter_link_aleatorio(links: List[str]) -> Optional[str]:
    """
    Retorna um link aleatório da lista de links de qualidade.

    Args:
        links (List[str]): Lista de URLs das diferentes qualidades.

    Returns:
        Optional[str]: URL aleatória selecionada ou None se a lista estiver vazia.
    """
    return random.choice(links) if links else None

def obter_playlist_qualidade(url: str, fingerprint: dict, bot_id: int = None) -> Optional[str]:
    """
    Obtém a playlist de uma qualidade específica.

    Args:
        url (str): URL da playlist de qualidade.
        fingerprint (dict): Dados do fingerprint para os headers.
        bot_id (int, optional): ID do bot para usar sua sessão específica.

    Returns:
        Optional[str]: Conteúdo da playlist ou None se ocorrer erro.
    """
    # Usar session_manager em vez de get_session
    session = session_manager.get_session(bot_id) if bot_id else requests.Session()
    
    headers = {
        "User-Agent": fingerprint.get('User-Agent'),
        "Client-ID": fingerprint.get('Client-Id'),
        "X-Device-Id": fingerprint.get('Device-Id'),
        "Accept": "application/x-mpegURL, application/vnd.apple.mpegurl, application/json, text/plain",
        "Accept-Language": "pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        "Origin": "https://www.twitch.tv",
        "Referer": "https://www.twitch.tv/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
    }

    try:
        response = session.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logging.error(f"BOT {bot_id}: Erro ao obter playlist de qualidade: {e}")
        return None

def extrair_segmentos_ts(playlist: str) -> List[str]:
    """
    Extrai os segmentos .ts da playlist de qualidade.

    Args:
        playlist (str): Conteúdo da playlist de qualidade.

    Returns:
        List[str]: Lista de URLs dos segmentos .ts.
    """
    return [linha for linha in playlist.split('\n') if linha.strip().endswith('.ts')]

def exibir_playlist_atualizada(playlist: str, max_linhas: int = 10) -> None:
    """
    Exibe a playlist atual no console de forma limitada.

    Args:
        playlist (str): Conteúdo da playlist.
        max_linhas (int): Número máximo de linhas para exibir.
    """
    print("\nPlaylist atualizada (primeiras linhas):")
    linhas = playlist.strip().split('\n')
    for i, linha in enumerate(linhas[:max_linhas], 1):
        print(f"   {i}: {linha}")
    if len(linhas) > max_linhas:
        print(f"   ... ({len(linhas) - max_linhas} linhas omitidas)")
    print()

def atualizar_playlist(canal_nome: str, token_data: dict, bot_id: int = None, limite_anuncios: int = None, check_limit_callback=None):
    """
    Atualiza continuamente a playlist e adiciona novos segmentos à fila.
    """
    fingerprint = session_manager.get_fingerprint(bot_id)
    segmentos_conhecidos = set()
    ultima_playlist = ""
    fila_segmentos = deque(maxlen=100)
    
    # Criar detector de anúncios com limite e callback
    ad_detector = create_ad_detector(max_total_ads=limite_anuncios if limite_anuncios else None, 
                                   check_limit_callback=check_limit_callback,
                                   bot_id=bot_id)

    # Contador para fila vazia
    fila_vazia_inicio = None
    TEMPO_MAXIMO_FILA_VAZIA = 30
    
    # Obter playlist inicial com retry
    sessao_tentativas = 0
    max_sessoes = 3
    playlist_m3u8 = None
    
    while sessao_tentativas < max_sessoes and not playlist_m3u8:
        playlist_m3u8, precisa_nova_sessao = tentar_obter_playlist_com_retry(canal_nome, token_data, bot_id)
        
        if not playlist_m3u8:
            if precisa_nova_sessao:
                sessao_tentativas += 1
                if sessao_tentativas < max_sessoes:
                    print(f"{WARNING_COLOR}Iniciando nova sessão ({sessao_tentativas}/{max_sessoes}){RESET}")
                    session_manager.close_session(bot_id)
                    continue
                else:
                    print(f"{ERROR_COLOR}Falha após {max_sessoes} tentativas de sessão{RESET}")
                    return None
            else:
                print(f"{ERROR_COLOR}Falha ao obter playlist inicial{RESET}")
                return None

    # Extrair link de qualidade
    links_qualidade = extrair_links_qualidade(playlist_m3u8)
    if not links_qualidade:
        print(f"{ERROR_COLOR}Nenhum link de qualidade encontrado{RESET}")
        return None

    link_qualidade = obter_link_aleatorio(links_qualidade)
    if not link_qualidade:
        print(f"{ERROR_COLOR}Falha ao selecionar qualidade{RESET}")
        return None

    # Iniciar downloader em thread separada
    iniciar_downloader(fila_segmentos, bot_id)

    rate_limiter = get_rate_limiter()
    
    while True:
        try:
            # Verifica se a fila está vazia
            if len(fila_segmentos) == 0:
                if fila_vazia_inicio is None:
                    fila_vazia_inicio = time.time()
                elif time.time() - fila_vazia_inicio > TEMPO_MAXIMO_FILA_VAZIA:
                    logger.warning(f"BOT {bot_id}: Fila vazia por mais de {TEMPO_MAXIMO_FILA_VAZIA}s. Reiniciando sessão...")
                    return False  # Retorna False para indicar que precisa reiniciar
            else:
                fila_vazia_inicio = None

            # Adquire permissão para atualizar playlist
            if not rate_limiter.acquire(bot_id, 'playlist'):
                logger.warning(f"BOT {bot_id}: Limite de atualizações atingido, aguardando...")
                time.sleep(2)
                continue
                
            playlist_qualidade = obter_playlist_qualidade(link_qualidade, fingerprint, bot_id)
            if not playlist_qualidade:
                print(f"{WARNING_COLOR}Tentativa de atualizar playlist falhou{RESET}")
                time.sleep(2)
                continue

            # Processar playlist para detectar anúncios
            ad_detector.process_playlist(playlist_qualidade)
            
            print("\n=== Playlist M3U8 (10 primeiras linhas) ===")
            linhas = playlist_qualidade.strip().split('\n')
            for i, linha in enumerate(linhas[:10], 1):
                linha_truncada = linha[:100] + "..." if len(linha) > 100 else linha
                print(f"{i:2}: {linha_truncada}")
            print("=" * 50 + "\n")

            novos_segmentos = extrair_segmentos_ts(playlist_qualidade)
            if not novos_segmentos:
                print(f"{WARNING_COLOR}Nenhum segmento encontrado na playlist{RESET}")
                time.sleep(2)
                continue

            if playlist_qualidade != ultima_playlist:
                segmentos_adicionados = 0
                for segmento in novos_segmentos:
                    if segmento not in segmentos_conhecidos:
                        segmentos_conhecidos.add(segmento)
                        fila_segmentos.append(segmento)
                        segmentos_adicionados += 1
                        
                if segmentos_adicionados > 0:
                    ultima_playlist = playlist_qualidade
                    print(f"{MAGENTA_COLOR}Playlist atualizada! +{segmentos_adicionados} segmentos{RESET}")
                else:
                    print(f"{WARNING_COLOR}Nenhum segmento novo encontrado{RESET}")
            else:
                print(f"{INFO_COLOR}Aguardando novos segmentos...{RESET}")
            time.sleep(2)

        except KeyboardInterrupt:
            print(f"\n{INFO_COLOR}Encerrando atualização de playlist...{RESET}")
            return True
        except Exception as e:
            print(f"{ERROR_COLOR}Erro ao atualizar playlist: {e}{RESET}")
            time.sleep(2)

        finally:
            rate_limiter.release(bot_id, 'playlist')
