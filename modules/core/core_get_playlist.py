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
    rate_limiter = get_rate_limiter()
    max_tentativas = 3
    tentativa = 0
    backoff_time = 2  # Tempo inicial de espera
    
    while tentativa < max_tentativas:
        try:
            if not rate_limiter.acquire(bot_id):
                logger.warning(f"BOT {bot_id}: Limite de requisições atingido...")
                time.sleep(1)
                continue
                
            session = get_session(bot_id)
            
            # Monta URL da playlist
            url = f"https://usher.ttvnw.net/api/channel/hls/{canal_nome}.m3u8"
            params = {
                'player': 'twitchweb',
                'token': token_data['value'],
                'sig': token_data['signature'],
                'allow_source': 'true',
                'allow_audio_only': 'false',
                'fast_bread': 'true'
            }
            
            response = session.get(url, params=params, timeout=5)
            
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:  # Rate limit
                    logger.error(f"BOT {bot_id}: Rate limit atingido na obtenção da playlist")
                elif response.status_code == 403:  # Forbidden
                    logger.error(f"BOT {bot_id}: Acesso negado na obtenção da playlist")
                elif response.status_code == 404:  # Not Found
                    logger.error(f"BOT {bot_id}: Canal não encontrado")
                else:
                    logger.error(f"BOT {bot_id}: Erro HTTP {response.status_code} na obtenção da playlist")
                
                tentativa += 1
                wait_time = backoff_time * (2 ** tentativa)
                logger.warning(f"BOT {bot_id}: Tentativa {tentativa}/{max_tentativas} falhou. "
                             f"Aguardando {wait_time}s antes da próxima tentativa")
                time.sleep(wait_time)
                continue
                
            return response.text
            
        except requests.exceptions.Timeout:
            tentativa += 1
            wait_time = backoff_time * (2 ** tentativa)
            logger.warning(f"BOT {bot_id}: Timeout ao obter playlist (tentativa {tentativa}/{max_tentativas}). "
                         f"Aguardando {wait_time}s...")
            time.sleep(wait_time)
            continue
            
        except requests.exceptions.ConnectionError:
            tentativa += 1
            logger.error(f"BOT {bot_id}: Erro de conexão ao obter playlist")
            time.sleep(2)
            continue
            
        except Exception as e:
            tentativa += 1
            logger.error(f"BOT {bot_id}: Erro ao obter playlist: {str(e)}")
            time.sleep(2)
            continue
            
        finally:
            rate_limiter.release(bot_id)
            
    # Se chegou aqui, todas as tentativas falharam
    logger.error(f"BOT {bot_id}: Todas as tentativas de obter playlist falharam")
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
