"""
Módulo para obter tokens de acesso de reprodução da Twitch.
"""

import sys
import os
from pathlib import Path
import requests
import json
import logging
from typing import Dict, Optional
import time
from modules.utils.utils_rate_limiter import get_rate_limiter
from modules.core.core_session import session_manager, get_session

logger = logging.getLogger(__name__)

# Adiciona o diretório raiz do projeto ao PYTHONPATH
root_dir = str(Path(__file__).parent.parent.parent)
sys.path.append(root_dir)

def get_playback_access_token_headers(fingerprint: Dict[str, str]) -> Dict[str, str]:
    """Headers para a requisição do token."""
    return {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': fingerprint.get('Accept-Language'),
        'Authorization': 'undefined',
        'Cache-Control': 'no-cache',
        'Client-Id': fingerprint.get('Client-Id'),
        'Content-Type': 'text/plain; charset=UTF-8',
        'Device-Id': fingerprint.get('Device-Id'),
        'Origin': 'https://www.twitch.tv',
        'Pragma': 'no-cache',
        'Priority': 'u=1, i',
        'Referer': 'https://www.twitch.tv/',
        'Sec-Ch-Ua': fingerprint.get('Sec-Ch-Ua'),
        'Sec-Ch-Ua-Mobile': fingerprint.get('Sec-Ch-Ua-Mobile'),
        'Sec-Ch-Ua-Platform': fingerprint.get('Sec-Ch-Ua-Platform'),
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': fingerprint.get('User-Agent')
    }

def criar_payload_playback_token(channel_name: str) -> Dict:
    """Cria o payload para a requisição do token."""
    return {
        "operationName": "PlaybackAccessToken_Template",
        "query": """
        query PlaybackAccessToken_Template($login: String!, $isLive: Boolean!, $vodID: ID!, $isVod: Boolean!, $playerType: String!, $platform: String!) {
          streamPlaybackAccessToken(channelName: $login, params: {platform: $platform, playerBackend: "mediaplayer", playerType: $playerType}) @include(if: $isLive) {
            value
            signature
            authorization {
              isForbidden
              forbiddenReasonCode
            }
            __typename
          }
          videoPlaybackAccessToken(id: $vodID, params: {platform: $platform, playerBackend: "mediaplayer", playerType: $playerType}) @include(if: $isVod) {
            value
            signature
            __typename
          }
        }
        """,
        "variables": {
            "isLive": True,
            "login": channel_name,
            "isVod": False,
            "vodID": "",
            "playerType": "site",
            "platform": "web"
        }
    }

def obter_playback_access_token(channel_name: str, fingerprint: dict, bot_id: int = None) -> Optional[dict]:
    """Obtém o token de acesso de reprodução."""
    rate_limiter = get_rate_limiter()
    backoff_time = 2
    tentativa = 0
    
    while True:  # Loop infinito
        try:
            if not rate_limiter.acquire(bot_id, 'playlist'):
                logger.warning(f"BOT {bot_id}: Limite de requisições de token atingido, aguardando...")
                time.sleep(2)
                continue
            
            from modules.core.core_session import get_session
            
            url = "https://gql.twitch.tv/gql"
            headers = get_playback_access_token_headers(fingerprint)
            payload = criar_payload_playback_token(channel_name)
            
            session = get_session(bot_id)
            
            response = session.post(url, headers=headers, json=payload)
            
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:
                    logger.error(f"BOT {bot_id}: Rate limit atingido na obtenção do token")
                elif response.status_code == 403:
                    logger.error(f"BOT {bot_id}: Acesso negado na obtenção do token")
                elif response.status_code == 404:
                    logger.error(f"BOT {bot_id}: Canal não encontrado")
                else:
                    logger.error(f"BOT {bot_id}: Erro HTTP {response.status_code}")
                raise
            
            response_text = response.text
            
            logger.info(f"BOT {bot_id}: Token Response: {response_text}", extra={'terminal': False})
            
            data = response.json()
            
            if 'data' in data and 'streamPlaybackAccessToken' in data['data']:
                token_data = data['data']['streamPlaybackAccessToken']
                
                try:
                    token_value = json.loads(token_data['value'])
                    user_ip = token_value.get('user_ip')
                    
                    # Log detalhado do token e IP
                    logger.info("", extra={
                        'token_response': json.dumps(token_value, indent=2),
                        'user_ip': user_ip,
                        'bot_id': bot_id
                    })
                    
                    if user_ip and bot_id:
                        from modules.utils.utils_bot_monitor import get_bot_monitor
                        monitor = get_bot_monitor()
                        monitor.update_bot_ip(bot_id, user_ip)
                    
                    logger.info(f"\nTOKEN RESPONSE - BOT {bot_id}:\nResponse: {token_data}\nExtracted IP: {user_ip}\n{'='*80}\n", extra={'terminal': False})
                    
                except Exception as e:
                    logger.error(f"BOT {bot_id}: Token parsing error: {str(e)}")
                
                return token_data
            else:
                logger.error("Falha ao obter token de acesso de reprodução")
                raise Exception("Token inválido")
        except Exception as e:
            wait_time = backoff_time * (2 ** (tentativa % 3))
            tentativa += 1
            
            logger.error(f"BOT {bot_id}: Erro ao obter token: {str(e)}")
            logger.warning(f"BOT {bot_id}: Tentativa {tentativa}. Aguardando {wait_time}s...")
            
            if tentativa % 3 == 0:
                session_manager.close_session(bot_id)
                logger.info(f"BOT {bot_id}: Trocando sessão após 3 falhas")
            
            time.sleep(wait_time)
            continue
            
        finally:
            rate_limiter.release(bot_id, 'playlist')

# Alias para compatibilidade
obter_token_acesso = obter_playback_access_token
