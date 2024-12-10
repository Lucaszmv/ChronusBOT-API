"""
Módulo para obter playlists M3U8 da Twitch.
"""
import sys
from pathlib import Path
import requests
import logging
import random
import time
from typing import Optional, Tuple
from colorama import Fore, Style, init
from modules.utils.utils_rate_limiter import get_rate_limiter

# Adiciona o diretório raiz do projeto ao PYTHONPATH
root_dir = str(Path(__file__).parent.parent.parent)
sys.path.append(root_dir)

try:
    from modules.core.core_session import get_session, session_manager
    from modules.utils.utils_failure_manager import get_failure_manager
except ImportError as e:
    logging.error(f"Erro ao importar módulos: {e}")
    sys.exit(1)

logger = logging.getLogger(__name__)

def obter_playlist_m3u8(canal_nome: str, token_data: dict, bot_id: int = None) -> Optional[str]:
    """
    Obtém a playlist M3U8 para um canal específico da Twitch com retry e recuperação de erros.

    Args:
        canal_nome (str): Nome do canal da Twitch.
        token_data (dict): Dados do token de acesso.
        bot_id (int, optional): ID do bot para usar sua sessão específica.

    Returns:
        Optional[str]: Conteúdo da playlist M3U8 ou None se ocorrer erro.
    """
    max_tentativas = 3
    tentativa = 0
    failure_mgr = get_failure_manager()
    rate_limiter = get_rate_limiter()
    
    while tentativa < max_tentativas:
        tentativa += 1
        try:
            # Adquire permissão do rate limiter
            if not rate_limiter.acquire(bot_id):
                logger.warning(f"BOT {bot_id}: Limite de requisições atingido, aguardando...")
                time.sleep(2)
                continue
                
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

            response = session.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            # Se chegou aqui, a requisição foi bem sucedida
            failure_mgr.register_success(bot_id)
            return response.text

        except requests.exceptions.RequestException as e:
            error_msg = f"Tentativa {tentativa}/{max_tentativas} falhou: {str(e)}"
            logging.error(error_msg)
            
            if failure_mgr.register_failure(bot_id, error_msg):
                logging.warning(f"BOT {bot_id}: Muitas falhas consecutivas, reiniciando sessão...")
                session_manager.close_session(bot_id)
                return None
            
            if tentativa < max_tentativas:
                wait_time = 2 ** tentativa  # Backoff exponencial
                logging.info(f"Aguardando {wait_time}s antes da próxima tentativa...")
                time.sleep(wait_time)
            else:
                logging.error("Todas as tentativas de obter playlist falharam")
                return None
                
        finally:
            # Libera o recurso do rate limiter
            rate_limiter.release(bot_id)

    return None

def tentar_obter_playlist_com_retry(canal_nome: str, token_data: dict, bot_id: int = None) -> Tuple[Optional[str], bool]:
    """
    Tenta obter a playlist com retry e gerenciamento de sessão.

    Args:
        canal_nome (str): Nome do canal da Twitch.
        token_data (dict): Dados do token de acesso.
        bot_id (int, optional): ID do bot para usar sua sessão específica.

    Returns:
        Tuple[Optional[str], bool]: (playlist, precisa_nova_sessao)
    """
    playlist = obter_playlist_m3u8(canal_nome, token_data, bot_id)
    
    if playlist is None:
        failure_mgr = get_failure_manager()
        if failure_mgr.should_restart_session(bot_id):
            return None, True
    
    return playlist, False
