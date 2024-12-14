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

# Adiciona o diretório raiz do projeto ao PYTHONPATH
root_dir = str(Path(__file__).parent.parent.parent)
sys.path.append(root_dir)

logger = logging.getLogger(__name__)

def get_playback_access_token_headers(fingerprint: Dict[str, str]) -> Dict[str, str]:
    """Headers para a requisição do token."""
    return {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip',
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
    
    try:
        # Adquire permissão para requisição de token
        if not rate_limiter.acquire(bot_id, 'playlist'):  # Usa mesmo limite de playlist por ser menos frequente
            logger.warning(f"BOT {bot_id}: Limite de requisições de token atingido, aguardando...")
            time.sleep(2)
            return None
            
        # Importação movida para dentro da função para evitar circular import
        from modules.core.core_session import get_session
        
        url = "https://gql.twitch.tv/gql"
        headers = get_playback_access_token_headers(fingerprint)
        payload = criar_payload_playback_token(channel_name)
        
        session = get_session(bot_id)
        
        response = session.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        if 'data' in data and 'streamPlaybackAccessToken' in data['data']:
            return data['data']['streamPlaybackAccessToken']
        else:
            logging.error("Falha ao obter token de acesso de reprodução")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro na requisição: {e}")
        return None
    finally:
        rate_limiter.release(bot_id, 'playlist')

# Alias para compatibilidade
obter_token_acesso = obter_playback_access_token
