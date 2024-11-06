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
from datetime import datetime, timezone
from collections import deque
import json

# Adiciona o diretório pai ao sys.path para importar os módulos necessários
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importações dos módulos core
from modules.core.core_fingerprint import get_fingerprint
from modules.core.core_token import obter_playback_access_token
from modules.core.core_get_playlist import obter_playlist_m3u8

# Importações dos módulos utils
from modules.utils.utils_segment_download import iniciar_downloader
from modules.utils.utils_ads_detector import create_ad_detector

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

def obter_playlist_qualidade(url: str, fingerprint: dict) -> Optional[str]:
    """
    Obtém a playlist de uma qualidade específica.

    Args:
        url (str): URL da playlist de qualidade.
        fingerprint (dict): Dados do fingerprint para os headers.

    Returns:
        Optional[str]: Conteúdo da playlist ou None se ocorrer erro.
    """
    headers = {
        "User-Agent": fingerprint.get('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'),
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
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
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

def exibir_playlist_atualizada(playlist: str):
    """
    Exibe a playlist atualizada completa no console.

    Args:
        playlist (str): Conteúdo da playlist a ser exibida.
    """
    print("\nPlaylist atualizada completa:")
    linhas = playlist.split('\n')
    for i, linha in enumerate(linhas):
        print(f"{i+1:4d}: {linha}")
    print()

def atualizar_playlist(canal_nome: str, token_data: dict, fingerprint: dict, intervalo: int = 2) -> None:
    """
    Atualiza a playlist a cada intervalo de tempo e adiciona novos segmentos a uma fila.

    Args:
        canal_nome (str): Nome do canal da Twitch.
        token_data (dict): Dados do token de acesso.
        fingerprint (dict): Dados do fingerprint.
        intervalo (int): Intervalo em segundos entre as atualizações (padrão: 2).
    """
    segmentos_conhecidos: Set[str] = set()
    fila_segmentos = deque()
    
    # Iniciar o simulador de download em uma thread separada
    iniciar_downloader(fila_segmentos)

    playlist_principal = obter_playlist_m3u8(canal_nome, token_data, fingerprint)
    
    if not playlist_principal:
        logging.error("Falha ao obter a playlist principal")
        return

    links_qualidade = extrair_links_qualidade(playlist_principal)
    if not links_qualidade:
        logging.error("Nenhum link de qualidade encontrado na playlist principal")
        return

    link_qualidade = obter_link_aleatorio(links_qualidade)
    ultima_playlist = ""
    ad_detector = create_ad_detector()

    while True:
        inicio_requisicao = time.time()
        
        headers = fingerprint
        logging.info(f"Headers da requisição para atualizar a playlist:\n{json.dumps(headers, indent=2)}")
        
        playlist_qualidade = obter_playlist_qualidade(link_qualidade, fingerprint)
        if not playlist_qualidade:
            logging.error("Falha ao obter a playlist de qualidade")
            time.sleep(intervalo)
            continue

        if playlist_qualidade != ultima_playlist:
            exibir_playlist_atualizada(playlist_qualidade)
            ultima_playlist = playlist_qualidade

        # Detectar anúncios
        ad_detector.process_playlist(playlist_qualidade)

        segmentos_ts = extrair_segmentos_ts(playlist_qualidade)
        novos_segmentos = [seg for seg in segmentos_ts if seg not in segmentos_conhecidos]

        if novos_segmentos:
            logging.info(f"Novos segmentos encontrados: {len(novos_segmentos)}")
            for segmento in novos_segmentos:
                if segmento not in fila_segmentos:
                    fila_segmentos.append(segmento)
            segmentos_conhecidos.update(novos_segmentos)

        logging.info(f"Tamanho atual da fila de segmentos: {len(fila_segmentos)}")

        tempo_decorrido = time.time() - inicio_requisicao
        tempo_espera = max(0, intervalo - tempo_decorrido)
        time.sleep(tempo_espera)

def main():
    """
    Função principal para teste do módulo.
    Configura logging e executa o processo de atualização da playlist.
    """
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f'playlist_updater_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.log')

    logging.basicConfig(filename=log_file, level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    try:
        canal_nome = input("Digite o nome do canal da Twitch: ")
        fingerprint = get_fingerprint()
        token_data = obter_playback_access_token(canal_nome, fingerprint)

        if token_data:
            print(f"Token de acesso obtido com sucesso para o canal {canal_nome}")
            atualizar_playlist(canal_nome, token_data, fingerprint)
        else:
            print("Falha ao obter o token de acesso. Verifique o arquivo de log.")
    except Exception as e:
        print(f"Ocorreu um erro durante a execução: {e}")
        print(f"Verifique o arquivo de log: {log_file}")

if __name__ == "__main__":
    main()
