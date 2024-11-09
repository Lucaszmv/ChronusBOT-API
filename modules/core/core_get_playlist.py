"""
Módulo para obter playlists M3U8 da Twitch.

Este módulo contém funções para criar headers, parâmetros e fazer requisições
para obter playlists M3U8 necessárias para reproduzir streams da Twitch.
"""

import sys
import os
from pathlib import Path

# Adiciona o diretório raiz do projeto ao PYTHONPATH
root_dir = str(Path(__file__).parent.parent.parent)
sys.path.append(root_dir)

import requests
import json
import logging
import time
import random
from datetime import datetime, timezone
from typing import Dict, Optional
from colorama import Fore, Style, init

# Inicializar o Colorama
init()

try:
    from modules.core.core_session import get_session
    from modules.core.core_token import obter_playback_access_token
except ImportError as e:
    logging.error(f"Erro ao importar módulos: {e}")
    print(f"Erro ao importar módulos. Verifique o arquivo de log.")
    sys.exit(1)

def obter_playlist_m3u8(canal_nome: str, token_data: dict, fingerprint: dict, bot_id: int = None) -> Optional[str]:
    """
    Obtém a playlist M3U8 para um canal específico da Twitch.

    Args:
        canal_nome (str): Nome do canal da Twitch.
        token_data (dict): Dados do token de acesso.
        fingerprint (dict): Dados do fingerprint.
        bot_id (int, optional): ID do bot para usar sua sessão específica.

    Returns:
        Optional[str]: Conteúdo da playlist M3U8 ou None se ocorrer um erro.
    """
    token = token_data['value']
    signature = token_data['signature']

    url = f"https://usher.ttvnw.net/api/channel/hls/{canal_nome}.m3u8"
    
    params = {
        "player": "twitchweb",
        "p": str(int(random.random() * 999999)),
        "type": "any",
        "allow_source": "true",
        "allow_audio_only": "true",
        "allow_spectre": "false",
        "fast_bread": "true",
        "sig": signature,
        "token": token,
    }
    
    headers = {
        "User-Agent": fingerprint.get('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'),
        "Client-ID": fingerprint.get('Client-Id'),
        "X-Device-Id": fingerprint.get('Device-Id')
    }
    
    try:
        # Obter a sessão específica do bot ou criar uma nova
        session = get_session(bot_id) if bot_id is not None else requests.Session()
        
        # Log da requisição
        logging.info(f"Obtendo playlist M3U8 para o canal: {canal_nome}")
        logging.info(f"Headers da requisição: {json.dumps(headers, indent=2)}")
        logging.info(f"Parâmetros da requisição: {json.dumps(params, indent=2)}")
        
        response = session.get(url, params=params, headers=headers)
        
        response.raise_for_status()
        
        # Log da resposta
        logging.info(f"Resposta recebida: Status {response.status_code}")
        logging.info(f"Headers da resposta: {json.dumps(dict(response.headers), indent=2)}")
        
        playlist = response.text
        logging.info(f"Playlist M3U8 completa para o canal {canal_nome}:\n{playlist}")
        
        return playlist
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao obter a playlist M3U8: {e}")
        return None

def testar_obter_playlist_m3u8(canal: str):
    """
    Testa a função de obtenção da playlist M3U8 para um canal específico.
    """
    from modules.core.core_session import session_manager
    
    logging.info(f"Testando obtenção de playlist M3U8 para o canal: {canal}")
    print(f"{Fore.YELLOW}Testando canal: {canal}{Style.RESET_ALL}")
    print("=" * 70)
    
    # Criar uma sessão de teste usando o SessionManager
    bot_id = 999  # ID específico para testes
    session = session_manager.get_session(bot_id)
    fingerprint = session_manager.get_fingerprint(bot_id)
    
    # Exibir informações do proxy
    if session.proxies:
        proxy_info = session.proxies.get('http', 'Nenhum proxy configurado')
        print(f"{Fore.CYAN}Proxy em uso: {proxy_info}{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}⚠️ Nenhum proxy configurado{Style.RESET_ALL}")
    print("=" * 70)
    
    print(f"{Fore.CYAN}Sessão de teste criada com bot_id: {bot_id}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Fingerprint gerado:{Style.RESET_ALL}")
    for key, value in fingerprint.items():
        print(f"{Fore.YELLOW}{key}:{Style.RESET_ALL} {value}")
    print("=" * 70)
    
    # Obter token de acesso usando a sessão criada
    token_data = obter_playback_access_token(canal, fingerprint, bot_id)
    
    if not token_data:
        logging.error(f"Não foi possível obter o token de acesso para o canal {canal}")
        print(f"Não foi possível obter o token de acesso para o canal {canal}")
        return
    
    # Obter playlist usando a mesma sessão
    playlist = obter_playlist_m3u8(canal, token_data, fingerprint, bot_id)
    
    if playlist:
        logging.info(f"{Fore.GREEN}✅ Playlist M3U8 obtida com sucesso para o canal {canal}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}✅ Playlist M3U8 obtida com sucesso para o canal {canal}{Style.RESET_ALL}")
        print("=" * 70)
        logging.info("Conteúdo da playlist M3U8:")
        logging.info(playlist)
        print(f"{Fore.YELLOW}\nPrimeiras 10 linhas da Playlist M3U8:{Style.RESET_ALL}")
        print("\n".join(playlist.split("\n")[:10]))
    else:
        logging.error(f"❌ Não foi possível obter a playlist M3U8 para o canal {canal}")
        print(f"❌ Não foi possível obter a playlist M3U8 para o canal {canal}")
    
    # Fechar a sessão de teste
    session_manager.close_session(bot_id)
    print(f"\n{Fore.GREEN}✅ Sessão de teste fechada{Style.RESET_ALL}")
    print("=" * 70)

# Exemplo de uso e teste
if __name__ == "__main__":
    try:
        # Configuração do logging
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f'playlist_requests_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.log')
        
        logging.basicConfig(filename=log_file, level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')
        
        canal_teste = input(f"{Fore.YELLOW}Digite o nome do canal da Twitch para testar: {Style.RESET_ALL}")
        testar_obter_playlist_m3u8(canal_teste)
        print(f"Todos os dados foram registrados no arquivo de log: {log_file}")
        print("=" * 70)
        time.sleep(60)
    except Exception as e:
        logging.error(f"❌ Erro durante a execução dos testes: {e}")
        print(f"❌ Ocorreu um erro durante a execução. Verifique o arquivo de log: {log_file}")
