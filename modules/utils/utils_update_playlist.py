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
    Obtém a playlist de uma qualidade específica com retry e backoff.

    Args:
        url (str): URL da playlist de qualidade.
        fingerprint (dict): Dados do fingerprint para os headers.
        bot_id (int, optional): ID do bot para usar sua sessão específica.

    Returns:
        Optional[str]: Conteúdo da playlist ou None se ocorrer erro.
    """
    max_tentativas = 3
    tentativa = 0
    backoff_time = 2  # Tempo inicial de espera
    
    while tentativa < max_tentativas:
        try:
            session = session_manager.get_session(bot_id)
            headers = {
                "User-Agent": fingerprint.get('User-Agent'),
                "Client-ID": fingerprint.get('Client-Id'),
                "X-Device-Id": fingerprint.get('Device-Id'),
                "Accept": "application/x-mpegURL, application/vnd.apple.mpegurl, application/json, text/plain",
                "Accept-Language": "pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3",
                "Accept-Encoding": "gzip, deflate, br",
                "Origin": "https://www.twitch.tv",
                "Referer": "https://www.twitch.tv/",
            }

            response = session.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            return response.text
            
        except requests.exceptions.HTTPError as e:
            tentativa += 1
            wait_time = backoff_time * (2 ** tentativa)
            
            if e.response.status_code == 429:
                logger.error(f"BOT {bot_id}: Rate limit atingido na playlist de qualidade")
            elif e.response.status_code == 403:
                logger.error(f"BOT {bot_id}: Acesso negado na playlist de qualidade")
            else:
                logger.error(f"BOT {bot_id}: Erro HTTP {e.response.status_code}")
                
            if tentativa < max_tentativas:
                logger.warning(f"BOT {bot_id}: Tentativa {tentativa}/{max_tentativas}. Aguardando {wait_time}s...")
                time.sleep(wait_time)
                continue
            return None
            
        except requests.exceptions.Timeout:
            tentativa += 1
            wait_time = backoff_time * (2 ** tentativa)
            logger.error(f"BOT {bot_id}: Timeout ao obter playlist de qualidade")
            if tentativa < max_tentativas:
                logger.warning(f"BOT {bot_id}: Tentativa {tentativa}/{max_tentativas}. Aguardando {wait_time}s...")
                time.sleep(wait_time)
                continue
            return None
            
        except Exception as e:
            tentativa += 1
            logger.error(f"BOT {bot_id}: Erro ao obter playlist de qualidade: {str(e)}")
            if tentativa < max_tentativas:
                time.sleep(2)
                continue
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
    """Atualiza a playlist e gerencia os segmentos com melhor tratamento de erros."""
    fingerprint = session_manager.get_fingerprint(bot_id)
    segmentos_conhecidos = set()
    ultima_playlist = ""
    fila_segmentos = deque(maxlen=1)
    ultimo_download = 0
    INTERVALO_DOWNLOAD = 10
    TEMPO_MAXIMO_FILA_VAZIA = 10
    MAX_TENTATIVAS_RECUPERACAO = 3
    TEMPO_ESPERA_ENTRE_TENTATIVAS = 2
    backoff_time = 2  # Tempo base para backoff
    
    # Configuração do detector de anúncios
    ad_detector = create_ad_detector(max_total_ads=limite_anuncios,
                                   check_limit_callback=check_limit_callback,
                                   bot_id=bot_id)

    # Inicialização de variáveis de controle
    fila_vazia_inicio = None
    tentativas_recuperacao = 0
    
    # Se for primeiro segmento, tenta com retry
    if primeiro_segmento:
        tentativas = 0
        max_tentativas = 3
        
        while tentativas < max_tentativas:
            try:
                playlist_m3u8, precisa_nova_sessao = tentar_obter_playlist_com_retry(canal_nome, token_data, bot_id)
                if not playlist_m3u8:
                    if precisa_nova_sessao:
                        session_manager.close_session(bot_id)
                        tentativas += 1
                        wait_time = backoff_time * (2 ** tentativas)
                        logger.warning(f"BOT {bot_id}: Tentativa {tentativas}/{max_tentativas}. "
                                     f"Aguardando {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    return False
                    
                links_qualidade = extrair_links_qualidade(playlist_m3u8)
                if not links_qualidade:
                    return False

                link_qualidade = obter_link_aleatorio(links_qualidade)
                if not link_qualidade:
                    return False
                    
                playlist_qualidade = obter_playlist_qualidade(link_qualidade, fingerprint, bot_id)
                if not playlist_qualidade:
                    return False
                    
                novos_segmentos = extrair_segmentos_ts(playlist_qualidade)
                if not novos_segmentos:
                    return False
                    
                if simular_download_segmento(novos_segmentos[0], bot_id):
                    return True
                return False
                
            except Exception as e:
                tentativas += 1
                wait_time = backoff_time * (2 ** tentativas)
                logger.error(f"BOT {bot_id}: Erro ao processar primeiro segmento: {str(e)}")
                if tentativas < max_tentativas:
                    time.sleep(wait_time)
                    continue
                return False
    
    # Obter playlist inicial com retry
    max_sessoes = 3
    sessao_atual = 0
    
    while sessao_atual < max_sessoes:
        try:
            # Tenta obter playlist com retry
            playlist_m3u8, precisa_nova_sessao = tentar_obter_playlist_com_retry(canal_nome, token_data, bot_id)
            if not playlist_m3u8:
                # Se falhou após as tentativas
                sessao_atual += 1
                if sessao_atual < max_sessoes:
                    wait_time = backoff_time * (2 ** sessao_atual)
                    logger.warning(f"BOT {bot_id}: Trocando para sessão {sessao_atual}/{max_sessoes}. "
                                 f"Aguardando {wait_time}s...")
                    session_manager.close_session(bot_id)
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"BOT {bot_id}: Todas as {max_sessoes} sessões falharam")
                    return None
                    
            # Se conseguiu a playlist, reseta contador
            sessao_atual = 0
            links_qualidade = extrair_links_qualidade(playlist_m3u8)
            if not links_qualidade:
                return None

            link_qualidade = obter_link_aleatorio(links_qualidade)
            if not link_qualidade:
                return None

            iniciar_downloader(fila_segmentos, bot_id)
            rate_limiter = get_rate_limiter()
            
            while True:
                try:
                    # Rate limit com backoff exponencial
                    tentativas_rate_limit = 0
                    while not rate_limiter.acquire(bot_id, 'playlist'):
                        wait_time = backoff_time * (2 ** tentativas_rate_limit)
                        logger.warning(f"BOT {bot_id}: Rate limit atingido, aguardando {wait_time}s...")
                        time.sleep(wait_time)
                        tentativas_rate_limit += 1
                        
                    # Obtém a playlist de qualidade com retry
                    playlist_qualidade = obter_playlist_qualidade(link_qualidade, fingerprint, bot_id)
                    if not playlist_qualidade:
                        logger.error(f"BOT {bot_id}: Falha ao obter playlist de qualidade")
                        time.sleep(TEMPO_ESPERA_ENTRE_TENTATIVAS)
                        continue

                    novos_segmentos = extrair_segmentos_ts(playlist_qualidade)
                    tempo_atual = time.time()
                    
                    if novos_segmentos and (tempo_atual - ultimo_download) >= INTERVALO_DOWNLOAD:
                        ultimo_segmento = novos_segmentos[-1]
                        
                        if ultimo_segmento not in segmentos_conhecidos:
                            fila_segmentos.clear()
                            fila_segmentos.append(ultimo_segmento)
                            segmentos_conhecidos.add(ultimo_segmento)
                            ultima_playlist = playlist_qualidade
                            fila_vazia_inicio = None
                            tentativas_recuperacao = 0
                            ultimo_download = tempo_atual
                            
                            segment_name = ultimo_segmento.split('/')[-1]
                            segment_name = segment_name.split('.ts')[0][-80:] + '.ts'
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            print(f"[BOT {bot_id}][{timestamp}] Novo segmento adicionado: {segment_name}")
                            logger.debug(f"BOT {bot_id}: Novo segmento adicionado: {ultimo_segmento}")

                    if len(fila_segmentos) == 0:
                        if fila_vazia_inicio is None:
                            fila_vazia_inicio = time.time()
                            logger.debug(f"BOT {bot_id}: Fila vazia detectada")
                        elif time.time() - fila_vazia_inicio > TEMPO_MAXIMO_FILA_VAZIA:
                            logger.error(f"BOT {bot_id}: Fila vazia por {TEMPO_MAXIMO_FILA_VAZIA}s")
                            if tentativas_recuperacao < MAX_TENTATIVAS_RECUPERACAO:
                                tentativas_recuperacao += 1
                                logger.info(f"BOT {bot_id}: Tentativa de recuperação {tentativas_recuperacao}/{MAX_TENTATIVAS_RECUPERACAO}")
                                time.sleep(TEMPO_ESPERA_ENTRE_TENTATIVAS)
                                continue
                            return False
                    
                    time.sleep(1.5)

                except requests.exceptions.HTTPError as e:
                    logger.error(f"BOT {bot_id}: Erro HTTP {e.response.status_code}")
                    time.sleep(TEMPO_ESPERA_ENTRE_TENTATIVAS)
                    
                except requests.exceptions.Timeout:
                    logger.error(f"BOT {bot_id}: Timeout na atualização")
                    time.sleep(TEMPO_ESPERA_ENTRE_TENTATIVAS)
                    
                except Exception as e:
                    logger.error(f"BOT {bot_id}: Erro ao atualizar playlist: {str(e)}")
                    time.sleep(TEMPO_ESPERA_ENTRE_TENTATIVAS)
                    
                finally:
                    rate_limiter.release(bot_id, 'playlist')

        except Exception as e:
            logger.error(f"BOT {bot_id}: Erro ao atualizar playlist: {str(e)}")
            time.sleep(backoff_time)
