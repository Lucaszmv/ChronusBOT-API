"""
Módulo para atualização e gerenciamento de playlists M3U8 da Twitch.

Este módulo contém funções para extrair, atualizar e processar playlists M3U8,
incluindo a extração de segmentos, detecção de anúncios e gerenciamento da
fila de download.

Functions:
    extrair_links_qualidade: Extrai links de qualidade da playlist principal.
    obter_link_aleatorio: Seleciona um link de qualidade aleatório.
    obter_playlist_qualidade: Obtém a playlist de uma qualidade específica.
    extrair_segmentos_ts: Extrai segmentos .ts da playlist.
    exibir_playlist_atualizada: Exibe a playlist atual no console.
    atualizar_playlist: Gerencia o processo de atualização contínua da playlist.
"""

import random
import time
import logging
from typing import List, Set, Optional
import requests
import os
import sys
from colorama import Fore, Style
from pathlib import Path
from datetime import datetime, timezone
from collections import deque
import json

# Adiciona o diretório raiz do projeto ao PYTHONPATH
root_dir = str(Path(__file__).parent.parent.parent)
sys.path.append(root_dir)

try:
    # Importações dos módulos core
    from modules.core.core_token import obter_playback_access_token
    from modules.core.core_get_playlist import obter_playlist_m3u8
    
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
        logging.error(f"Erro ao obter playlist de qualidade: {e}")
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

def atualizar_playlist(canal_nome: str, token_data: dict, bot_id: int = None, max_atualizacoes: int = 2) -> dict:
    """
    Atualiza a playlist um número limitado de vezes.
    
    Args:
        canal_nome (str): Nome do canal da Twitch
        token_data (dict): Dados do token de acesso
        bot_id (int, optional): ID do bot para usar sua sessão específica
        max_atualizacoes (int): Número máximo de atualizações a realizar
        
    Returns:
        dict: Estatísticas da atualização {
            'atualizacoes': int,
            'segmentos_encontrados': int,
            'tentativas': int,
            'ultima_playlist': str
        }
    """
    fingerprint = session_manager.get_fingerprint(bot_id) if bot_id else None
    
    segmentos_conhecidos: Set[str] = set()
    fila_segmentos = deque()
    
    # Iniciar o simulador de download em uma thread separada
    iniciar_downloader(fila_segmentos, bot_id)

    playlist_principal = obter_playlist_m3u8(canal_nome, token_data, bot_id)
    if not playlist_principal:
        logger.error("Falha ao obter a playlist principal")
        return None

    links_qualidade = extrair_links_qualidade(playlist_principal)
    if not links_qualidade:
        logger.error("Nenhum link de qualidade encontrado")
        return None

    link_qualidade = obter_link_aleatorio(links_qualidade)
    if not link_qualidade:
        logger.error("Falha ao selecionar qualidade")
        return None
    
    ultima_playlist = ""
    ad_detector = create_ad_detector()
    atualizacoes = 0
    tentativas = 0
    max_tentativas = 10

    while atualizacoes < max_atualizacoes and tentativas < max_tentativas:
        playlist_qualidade = obter_playlist_qualidade(link_qualidade, fingerprint, bot_id)
        if not playlist_qualidade:
            logger.warning(f"Tentativa {tentativas + 1}: Falha ao obter playlist")
            time.sleep(2)
            tentativas += 1
            continue

        novos_segmentos = extrair_segmentos_ts(playlist_qualidade)
        if not novos_segmentos:
            logger.warning(f"Tentativa {tentativas + 1}: Nenhum segmento encontrado")
            time.sleep(2)
            tentativas += 1
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
                ad_detector.process_playlist(playlist_qualidade)
                atualizacoes += 1
                logger.info(f"Adicionados {segmentos_adicionados} novos segmentos")
            else:
                logger.warning("Nenhum segmento novo encontrado")
                tentativas += 1
        else:
            logger.warning("Playlist não mudou desde última verificação")
            tentativas += 1

        time.sleep(2)

    return {
        'atualizacoes': atualizacoes,
        'segmentos_encontrados': len(segmentos_conhecidos),
        'tentativas': tentativas,
        'ultima_playlist': ultima_playlist
    }
