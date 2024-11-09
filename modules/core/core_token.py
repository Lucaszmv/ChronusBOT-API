"""
Módulo para obter tokens de acesso de reprodução da Twitch.

Este módulo contém funções para criar headers, payload e fazer requisições
para obter tokens de acesso necessários para reproduzir streams da Twitch.
"""

import sys
import os
from pathlib import Path
import requests
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict
from colorama import Fore, Style, init

# Adiciona o diretório raiz do projeto ao PYTHONPATH
root_dir = str(Path(__file__).parent.parent.parent)
sys.path.append(root_dir)

# Inicializar o Colorama
init()

# Importações locais
try:
    from modules.core.core_session import get_session, session_manager
except ImportError as e:
    logging.error(f"Erro ao importar módulos locais: {e}")
    print(f"Erro ao importar módulos. Verifique o arquivo de log.")
    sys.exit(1)

def get_playback_access_token_headers(fingerprint: Dict[str, str]) -> Dict[str, str]:
    """
    Retorna os headers para a requisição do token de acesso.

    Args:
        fingerprint (Dict[str, str]): Fingerprint gerado pelo fingerprint_generator.

    Returns:
        Dict[str, str]: Headers para a requisição de token.
    """
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
    """
    Cria o payload para a requisição do token de acesso.

    Args:
        channel_name (str): Nome do canal da Twitch.

    Returns:
        Dict: Payload da requisição.
    """
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

def obter_playback_access_token(channel_name: str, fingerprint: dict, bot_id: int = None, proxy: str = None) -> dict:
    """
    Obtém o token de acesso de reprodução para um canal específico da Twitch.

    Args:
        channel_name (str): Nome do canal da Twitch.
        fingerprint (dict): Dados do fingerprint.
        bot_id (int, optional): ID do bot para usar sua sessão específica.
        proxy (str, optional): Proxy para a sessão.

    Returns:
        dict: Token de acesso e dados relacionados ou None se ocorrer erro.
    """
    url = "https://gql.twitch.tv/gql"
    headers = get_playback_access_token_headers(fingerprint)
    payload = criar_payload_playback_token(channel_name)
    
    # Usar get_session em vez da sessão global
    session = get_session(bot_id)
    
    try:
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

obter_token_acesso = obter_playback_access_token

def testar_obter_playback_access_token(canal: str):
    """
    Testa a função de obtenção do token de acesso para um canal específico.

    Args:
        canal (str): Nome do canal da Twitch para testar.
    """
    from modules.core.core_session import session_manager  # Importa o gerenciador de sessões
    
    logging.info(f"Testando obtenção de token para o canal: {canal}")
    print(f"{Fore.YELLOW}Testando canal: {canal}{Style.RESET_ALL}")
    print("=" * 70)
    
    # Criar uma sessão de teste usando o SessionManager
    bot_id = 999  # ID específico para testes
    session = session_manager.get_session(bot_id)
    fingerprint = session_manager.get_fingerprint(bot_id)
    
    print(f"{Fore.CYAN}Sessão de teste criada com bot_id: {bot_id}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Fingerprint gerado:{Style.RESET_ALL}")
    for key, value in fingerprint.items():
        print(f"{Fore.YELLOW}{key}:{Style.RESET_ALL} {value}")
    print("=" * 70)
    
    # Obter token usando a sessão criada
    token = obter_playback_access_token(canal, fingerprint, bot_id)
    
    if token:
        logging.info(f"{Fore.GREEN}✅ Token obtido com sucesso para o canal {canal}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}✅ Token obtido com sucesso para o canal {canal}{Style.RESET_ALL}")
        logging.info(f"Assinatura: {token['signature']}")
        print(f"Assinatura: {token['signature']}")
        print("=" * 70)
        
        # Decodifica e exibe o conteúdo do token
        token_decodificado = json.loads(token['value'])
        logging.info("Conteúdo do token:")
        logging.info(json.dumps(token_decodificado, indent=2))
        print(f"{Fore.YELLOW}Conteúdo do token:{Style.RESET_ALL}")
        for chave, valor in token_decodificado.items():
            print(f"{chave}: {valor}")
        
        # Verifica a autorização
        auth = token['authorization']
        logging.info(f"Autorização: {json.dumps(auth, indent=2)}")
        print(f"{Fore.YELLOW}\nAutorização:{Style.RESET_ALL}")
        print(f"Proibido: {auth['isForbidden']}")
        print(f"Código de razão: {auth['forbiddenReasonCode']}")
    else:
        logging.error(f"❌ Não foi possível obter o token para o canal {canal}")
        print(f"❌ Não foi possível obter o token para o canal {canal}")
    
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
        log_file = os.path.join(log_dir, f'token_requests_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.log')
        
        logging.basicConfig(filename=log_file, level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')
        
        canal_teste = input(f"{Fore.YELLOW}Digite o nome do canal da Twitch para testar: {Style.RESET_ALL}")
        testar_obter_playback_access_token(canal_teste)
        print(f"Todos os dados foram registrados no arquivo de log: {log_file}")
        print("=" * 70)
        time.sleep(60)
    except Exception as e:
        logging.error(f"❌ Erro durante a execução dos testes: {e}")
        print(f"{Fore.RED}❌ Ocorreu um erro durante a execução. Verifique o arquivo de log: {log_file}{Style.RESET_ALL}")
