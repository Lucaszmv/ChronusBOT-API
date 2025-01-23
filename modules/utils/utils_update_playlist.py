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
from modules.utils.utils_segment_download import simular_download_segmento

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
    """Função mantida para compatibilidade, mas não exibe nada."""
    pass

def atualizar_playlist(canal_nome: str, token_data: dict, bot_id: int = None, 
                      limite_anuncios: int = None, check_limit_callback=None,
                      primeiro_segmento: bool = False):
    """Atualiza a playlist e gerencia os segmentos."""
    fingerprint = session_manager.get_fingerprint(bot_id)
    segmentos_conhecidos = set()
    ultima_playlist = ""
    fila_segmentos = deque(maxlen=1)
    ultimo_download = 0  # Timestamp do último download
    INTERVALO_DOWNLOAD = 10  # Intervalo de 10 segundos entre downloads
    
    # Se for o primeiro segmento, tenta baixar apenas um e retorna
    if primeiro_segmento:
        try:
            # Obter playlist inicial com retry
            playlist_m3u8, precisa_nova_sessao = tentar_obter_playlist_com_retry(canal_nome, token_data, bot_id)
            if not playlist_m3u8:
                return False
                
            # Extrair link de qualidade
            links_qualidade = extrair_links_qualidade(playlist_m3u8)
            if not links_qualidade:
                return False

            link_qualidade = obter_link_aleatorio(links_qualidade)
            if not link_qualidade:
                return False
                
            # Obtém a playlist de qualidade
            playlist_qualidade = obter_playlist_qualidade(link_qualidade, fingerprint, bot_id)
            if not playlist_qualidade:
                return False
                
            # Extrai segmentos
            novos_segmentos = extrair_segmentos_ts(playlist_qualidade)
            if not novos_segmentos:
                return False
                
            # Tenta baixar o primeiro segmento
            primeiro_segmento = novos_segmentos[0]
            if simular_download_segmento(primeiro_segmento, bot_id):
                return True
            return False
            
        except Exception as e:
            logger.error(f"BOT {bot_id}: Erro ao baixar primeiro segmento: {str(e)}")
            return False
            
    ad_detector = create_ad_detector(max_total_ads=limite_anuncios if limite_anuncios else None, 
                                   check_limit_callback=check_limit_callback,
                                   bot_id=bot_id)

    fila_vazia_inicio = None
    TEMPO_MAXIMO_FILA_VAZIA = 10  # Reduzido para 10 segundos
    tentativas_recuperacao = 0
    TEMPO_ESPERA_ENTRE_TENTATIVAS = 2
    MAX_TENTATIVAS_RECUPERACAO = 3
    
    def tentar_recuperar_playlist():
        nonlocal token_data, link_qualidade
        novo_token = obter_playback_access_token(canal_nome, fingerprint, bot_id)
        if not novo_token:
            return False
        token_data = novo_token
        
        nova_playlist = obter_playlist_m3u8(canal_nome, token_data, bot_id)
        if not nova_playlist:
            return False
            
        novos_links = extrair_links_qualidade(nova_playlist)
        if not novos_links:
            return False
        link_qualidade = obter_link_aleatorio(novos_links)
        
        playlist_qualidade = obter_playlist_qualidade(link_qualidade, fingerprint, bot_id)
        if not playlist_qualidade:
            return False
            
        novos_segmentos = extrair_segmentos_ts(playlist_qualidade)
        if not novos_segmentos:
            return False
            
        return True

    # Obter playlist inicial com retry
    sessao_tentativas = 0
    max_sessoes = 3
    playlist_m3u8 = None
    
    while sessao_tentativas < max_sessoes and not playlist_m3u8:
        playlist_m3u8, precisa_nova_sessao = tentar_obter_playlist_com_retry(canal_nome, token_data, bot_id)
        
        if not playlist_m3u8:
            if precisa_nova_sessao:
                sessao_tentativas += 1
                if sessao_tentativas >= max_sessoes:
                    return None
                session_manager.close_session(bot_id)
                continue
            else:
                return None

    # Extrair link de qualidade
    links_qualidade = extrair_links_qualidade(playlist_m3u8)
    if not links_qualidade:
        return None

    link_qualidade = obter_link_aleatorio(links_qualidade)
    if not link_qualidade:
        return None

    # Iniciar downloader em thread separada
    iniciar_downloader(fila_segmentos, bot_id)

    rate_limiter = get_rate_limiter()
    
    while True:
        try:
            # Adquire permissão para atualizar playlist
            if not rate_limiter.acquire(bot_id, 'playlist'):
                time.sleep(1)
                continue
                
            # Obtém a playlist de qualidade
            playlist_qualidade = obter_playlist_qualidade(link_qualidade, fingerprint, bot_id)
            if not playlist_qualidade:
                logger.error(f"BOT {bot_id}: Falha ao obter playlist de qualidade")
                time.sleep(TEMPO_ESPERA_ENTRE_TENTATIVAS)
                continue

            # Extrai segmentos e pega apenas o mais recente
            novos_segmentos = extrair_segmentos_ts(playlist_qualidade)
            tempo_atual = time.time()
            
            if novos_segmentos and (tempo_atual - ultimo_download) >= INTERVALO_DOWNLOAD:
                # Pega apenas o segmento mais recente
                ultimo_segmento = novos_segmentos[-1]
                
                if ultimo_segmento not in segmentos_conhecidos:
                    # Limpa a fila e adiciona apenas o novo segmento
                    fila_segmentos.clear()
                    fila_segmentos.append(ultimo_segmento)
                    segmentos_conhecidos.add(ultimo_segmento)
                    ultima_playlist = playlist_qualidade
                    fila_vazia_inicio = None
                    tentativas_recuperacao = 0
                    ultimo_download = tempo_atual
                    # Extrair apenas os últimos caracteres antes do .ts
                    segment_name = ultimo_segmento.split('/')[-1]
                    segment_name = segment_name.split('.ts')[0][-80:] + '.ts'
                    # Adiciona timestamp
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[BOT {bot_id}][{timestamp}] Novo segmento adicionado para download: {segment_name}")
                    
                    # Remove o logger.info e usa apenas o logger.debug para o log completo
                    logger.debug(f"BOT {bot_id}: Novo segmento adicionado para download: {ultimo_segmento}")

            # Verifica se a fila está vazia
            if len(fila_segmentos) == 0:
                if fila_vazia_inicio is None:
                    fila_vazia_inicio = time.time()
                    logger.debug(f"BOT {bot_id}: Fila vazia detectada, iniciando contagem...")  # Mudado para debug
                elif time.time() - fila_vazia_inicio > TEMPO_MAXIMO_FILA_VAZIA:
                    logger.error(f"BOT {bot_id}: Fila permaneceu vazia por {TEMPO_MAXIMO_FILA_VAZIA}s")
                    if tentativas_recuperacao < MAX_TENTATIVAS_RECUPERACAO:
                        tentativas_recuperacao += 1
                        logger.info(f"BOT {bot_id}: Tentativa de recuperação {tentativas_recuperacao}/{MAX_TENTATIVAS_RECUPERACAO}")
                        session_manager.close_session(bot_id)
                        time.sleep(TEMPO_ESPERA_ENTRE_TENTATIVAS)
                        continue
                    return False
            
            time.sleep(1.5)  # Intervalo entre verificações da playlist

        except Exception as e:
            logger.error(f"BOT {bot_id}: Erro ao atualizar playlist: {str(e)}")
            time.sleep(TEMPO_ESPERA_ENTRE_TENTATIVAS)
            
        finally:
            rate_limiter.release(bot_id, 'playlist')

    # Se for o primeiro segmento, tenta baixar apenas um e retorna
    if primeiro_segmento:
        try:
            playlist_qualidade = obter_playlist_qualidade(link_qualidade, fingerprint, bot_id)
            if not playlist_qualidade:
                return False
                
            novos_segmentos = extrair_segmentos_ts(playlist_qualidade)
            if not novos_segmentos:
                return False
                
            # Tenta baixar o primeiro segmento
            if simular_download_segmento(novos_segmentos[0], bot_id):
                return True
            return False
            
        except Exception as e:
            logger.error(f"BOT {bot_id}: Erro ao baixar primeiro segmento: {str(e)}")
            return False
