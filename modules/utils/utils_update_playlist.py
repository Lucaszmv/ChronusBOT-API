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
        "X-Device-Id": fingerprint.get('Device-Id')
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

def atualizar_playlist(canal_nome: str, token_data: dict, bot_id: int = None, max_atualizacoes: int = 2) -> None:
    """
    Atualiza a playlist um número limitado de vezes.
    """
    fingerprint = session_manager.get_fingerprint(bot_id) if bot_id else None
    
    segmentos_conhecidos: Set[str] = set()
    fila_segmentos = deque()
    
    # Iniciar o simulador de download em uma thread separada
    iniciar_downloader(fila_segmentos)

    playlist_principal = obter_playlist_m3u8(canal_nome, token_data, bot_id)
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
    atualizacoes = 0
    tentativas = 0
    max_tentativas = 10  # Limite de tentativas para evitar loop infinito

    while atualizacoes < max_atualizacoes and tentativas < max_tentativas:
        inicio_requisicao = time.time()
        
        playlist_qualidade = obter_playlist_qualidade(link_qualidade, fingerprint, bot_id)
        if not playlist_qualidade:
            logging.error("Falha ao obter a playlist de qualidade")
            time.sleep(2)
            tentativas += 1
            continue

        if playlist_qualidade != ultima_playlist:
            novos_segmentos = extrair_segmentos_ts(playlist_qualidade)
            if novos_segmentos:  # Verifica se há novos segmentos
                for segmento in novos_segmentos:
                    if segmento not in segmentos_conhecidos:
                        segmentos_conhecidos.add(segmento)
                        fila_segmentos.append(segmento)
                        print(f"{Fore.GREEN}Novo segmento adicionado à fila: {segmento[:50]}...{Style.RESET_ALL}")
                
                ultima_playlist = playlist_qualidade
                exibir_playlist_atualizada(playlist_qualidade)
                ad_detector.process_playlist(playlist_qualidade)
                atualizacoes += 1
                
                print(f"Tamanho da fila: {len(fila_segmentos)}, Atualização {atualizacoes}/{max_atualizacoes}")
            else:
                print(f"{Fore.YELLOW}Nenhum segmento novo encontrado na playlist{Style.RESET_ALL}")
                tentativas += 1
        else:
            print(f"{Fore.YELLOW}Playlist não mudou desde a última verificação{Style.RESET_ALL}")
            tentativas += 1

        tempo_decorrido = time.time() - inicio_requisicao
        tempo_espera = max(0, 2 - tempo_decorrido)
        time.sleep(tempo_espera)

    if tentativas >= max_tentativas:
        print(f"{Fore.RED}Limite de tentativas atingido sem sucesso na atualização da playlist{Style.RESET_ALL}")
    
    print(f"\n{Fore.GREEN}✅ Teste concluído: {atualizacoes} atualizações realizadas{Style.RESET_ALL}")

def main():
    """
    Função principal para teste do módulo.
    """
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f'playlist_updater_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.log')

    logging.basicConfig(filename=log_file, level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    try:
        print(f"{Fore.YELLOW}Testando Atualizador de Playlist...{Style.RESET_ALL}")
        print("=" * 70)
        
        canal_nome = input(f"{Fore.YELLOW}Digite o nome do canal da Twitch: {Style.RESET_ALL}")
        logging.info(f"Iniciando teste para o canal: {canal_nome}")
        
        # Criar sessão de teste
        bot_id = 999  # ID específico para testes
        session = session_manager.get_session(bot_id)
        fingerprint = session_manager.get_fingerprint(bot_id)
        
        print(f"\n{Fore.CYAN}Sessão de teste criada com bot_id: {bot_id}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Fingerprint gerado:{Style.RESET_ALL}")
        for key, value in fingerprint.items():
            print(f"{Fore.YELLOW}{key}:{Style.RESET_ALL} {value}")
            logging.info(f"Fingerprint - {key}: {value}")
        print("=" * 70)
        
        # Exibir informações do proxy
        if session.proxies:
            proxy_info = session.proxies.get('http', 'Nenhum proxy configurado')
            print(f"{Fore.CYAN}Proxy em uso: {proxy_info}{Style.RESET_ALL}")
            logging.info(f"Proxy em uso: {proxy_info}")
        else:
            print(f"{Fore.YELLOW}⚠️ Nenhum proxy configurado{Style.RESET_ALL}")
            logging.info("Nenhum proxy configurado")
        print("=" * 70)
        
        # Obter token usando a sessão criada
        print(f"{Fore.CYAN}Obtendo token de acesso...{Style.RESET_ALL}")
        token_data = obter_playback_access_token(canal_nome, fingerprint, bot_id)

        if token_data:
            print(f"{Fore.GREEN}✅ Token de acesso obtido com sucesso{Style.RESET_ALL}")
            logging.info("Token de acesso obtido com sucesso")
            
            print(f"\n{Fore.CYAN}Iniciando atualização de playlist...{Style.RESET_ALL}")
            logging.info("Iniciando processo de atualização de playlist")
            
            atualizar_playlist(canal_nome, token_data, bot_id)
        else:
            print(f"{Fore.RED}❌ Falha ao obter o token de acesso{Style.RESET_ALL}")
            logging.error("Falha ao obter o token de acesso")
            
        # Fechar a sessão ao finalizar
        session_manager.close_session(bot_id)
        print(f"{Fore.GREEN}✅ Sessão de teste fechada{Style.RESET_ALL}")
        logging.info("Sessão de teste fechada")
        print("=" * 70)
        print(f"Todos os dados foram registrados no arquivo de log: {log_file}")
        print("=" * 70)
        time.sleep(60)
        
    except Exception as e:
        logging.error(f"Erro durante a execução: {e}")
        print(f"{Fore.RED}❌ Ocorreu um erro durante a execução: {e}")
        print(f"Verifique o arquivo de log: {log_file}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
