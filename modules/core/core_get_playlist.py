"""
Módulo para obter playlists M3U8 da Twitch.
"""
import sys
from pathlib import Path
import requests
import logging
import random
from typing import Optional
from colorama import Fore, Style, init

# Adiciona o diretório raiz do projeto ao PYTHONPATH
root_dir = str(Path(__file__).parent.parent.parent)
sys.path.append(root_dir)

try:
    from modules.core.core_session import get_session, session_manager
except ImportError as e:
    logging.error(f"Erro ao importar módulos: {e}")
    sys.exit(1)

def obter_playlist_m3u8(canal_nome: str, token_data: dict, bot_id: int = None) -> Optional[str]:
    """
    Obtém a playlist M3U8 para um canal específico da Twitch.

    Args:
        canal_nome (str): Nome do canal da Twitch.
        token_data (dict): Dados do token de acesso.
        bot_id (int, optional): ID do bot para usar sua sessão específica.

    Returns:
        Optional[str]: Conteúdo da playlist M3U8 ou None se ocorrer um erro.
    """
    token = token_data['value']
    signature = token_data['signature']
    
    session = get_session(bot_id)
    fingerprint = session_manager.get_fingerprint(bot_id)

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
        "User-Agent": fingerprint.get('User-Agent'),
        "Client-ID": fingerprint.get('Client-Id'),
        "X-Device-Id": fingerprint.get('Device-Id')
    }
    
    try:
        response = session.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logging.debug(f"Erro ao obter playlist M3U8: {e}")  # Log básico apenas para debug
        return None
